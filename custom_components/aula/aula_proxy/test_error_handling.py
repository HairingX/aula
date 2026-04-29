"""Tests for error handling and 401 retry logic.

Verifies the core safety property: transient errors must NOT trigger MitID
re-authentication (AulaCredentialError / ConfigEntryAuthFailed), while genuine
credential failures MUST still trigger it.
"""
import json
import time
import threading
import unittest
from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch, PropertyMock

from requests import Response
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout

from custom_components.aula.aula_proxy.aula_errors import AulaApiError, AulaCredentialError
from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient


def _make_response(status_code: int, json_body: dict | list | None = None, text: str = "") -> Mock:
    """Build a mock Response with a given status code and optional JSON body."""
    resp = Mock(spec=Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.reason = HTTPStatus(status_code).phrase if status_code in [s.value for s in HTTPStatus] else ""
    resp.text = text or json.dumps(json_body) if json_body is not None else ""
    if json_body is not None:
        resp.json = Mock(return_value=json_body)
    else:
        resp.json = Mock(side_effect=json.JSONDecodeError("", "", 0))
    # request attribute for logging
    req = Mock()
    req.url = "https://example.com/api"
    req.headers = {}
    req.body = None
    resp.request = req
    return resp


# ---------------------------------------------------------------------------
# _retry_on_401
# ---------------------------------------------------------------------------

class TestRetryOn401(unittest.TestCase):
    """Tests for AulaProxyClient._retry_on_401."""

    def setUp(self):
        self.client = AulaProxyClient("test-token")

    def test_successful_retry_after_transient_401(self):
        """Transient 401 → refresh succeeds → retry returns 200."""
        resp_401 = _make_response(401)
        resp_200 = _make_response(200, {"data": []})
        callback = Mock(return_value=True)
        request_fn = Mock(return_value=resp_200)

        self.client.set_token_refresh_callback(callback)
        result = self.client._retry_on_401(resp_401, request_fn)

        self.assertEqual(result.status_code, 200)
        callback.assert_called_once()
        request_fn.assert_called_once()

    def test_callback_returns_false_raises_connection_error(self):
        """Transient refresh failure → raises ConnectionError (not reauth)."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=False)
        request_fn = Mock()

        self.client.set_token_refresh_callback(callback)
        with self.assertRaises(ConnectionError):
            self.client._retry_on_401(resp_401, request_fn)
        request_fn.assert_not_called()

    def test_no_callback_set(self):
        """No callback → returns original response unchanged."""
        resp_401 = _make_response(401)
        result = self.client._retry_on_401(resp_401, Mock())
        self.assertIs(result, resp_401)

    def test_non_401_passes_through(self):
        """Non-401 responses are returned unchanged without invoking callback."""
        resp_500 = _make_response(500)
        callback = Mock()
        self.client.set_token_refresh_callback(callback)

        result = self.client._retry_on_401(resp_500, Mock())

        self.assertIs(result, resp_500)
        callback.assert_not_called()

    def test_none_response_passes_through(self):
        result = self.client._retry_on_401(None, Mock())
        self.assertIsNone(result)

    def test_retry_network_error_raises_connection_error(self):
        """If the retry request fails with a network error, raise ConnectionError (not reauth)."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=True)
        request_fn = Mock(side_effect=RequestsConnectionError("conn error"))

        self.client.set_token_refresh_callback(callback)
        with self.assertRaises(ConnectionError):
            self.client._retry_on_401(resp_401, request_fn)

    def test_retry_timeout_raises_connection_error(self):
        """If the retry request times out, raise ConnectionError (not reauth)."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=True)
        request_fn = Mock(side_effect=RequestsTimeout("timeout"))

        self.client.set_token_refresh_callback(callback)
        with self.assertRaises(ConnectionError):
            self.client._retry_on_401(resp_401, request_fn)

    def test_retry_still_401_raises_connection_error(self):
        """If retry also returns 401, raise ConnectionError — token was just refreshed so this is transient."""
        resp_401 = _make_response(401)
        retry_401 = _make_response(401)
        callback = Mock(return_value=True)
        request_fn = Mock(return_value=retry_401)

        self.client.set_token_refresh_callback(callback)
        with self.assertRaises(ConnectionError):
            self.client._retry_on_401(resp_401, request_fn)

    def test_retry_non_401_error_returned(self):
        """If retry returns a non-401 error (e.g. 500), return it for normal error handling."""
        resp_401 = _make_response(401)
        resp_500 = _make_response(500)
        callback = Mock(return_value=True)
        request_fn = Mock(return_value=resp_500)

        self.client.set_token_refresh_callback(callback)
        result = self.client._retry_on_401(resp_401, request_fn)
        self.assertEqual(result.status_code, 500)

    def test_callback_credential_error_propagates(self):
        """AulaCredentialError from callback propagates (triggers reauth)."""
        resp_401 = _make_response(401)
        callback = Mock(side_effect=AulaCredentialError("expired"))

        self.client.set_token_refresh_callback(callback)
        with self.assertRaises(AulaCredentialError):
            self.client._retry_on_401(resp_401, Mock())


# ---------------------------------------------------------------------------
# _raise_error
# ---------------------------------------------------------------------------

class TestRaiseError(unittest.TestCase):
    """Tests for AulaProxyClient._raise_error."""

    def test_401_raises_credential_error(self):
        resp = _make_response(401, {"status": {"message": "Unauthorized"}})
        with self.assertRaises(AulaCredentialError):
            AulaProxyClient._raise_error(resp)

    def test_402_raises_permission_error(self):
        resp = _make_response(402)
        with self.assertRaises(PermissionError):
            AulaProxyClient._raise_error(resp)

    def test_403_raises_permission_error(self):
        resp = _make_response(403)
        with self.assertRaises(PermissionError):
            AulaProxyClient._raise_error(resp)

    def test_500_raises_api_error_not_credential(self):
        """Server errors must raise AulaApiError, NOT AulaCredentialError."""
        resp = _make_response(500)
        with self.assertRaises(AulaApiError):
            AulaProxyClient._raise_error(resp)
        # Must NOT raise AulaCredentialError
        with self.assertRaises(AulaApiError) as ctx:
            AulaProxyClient._raise_error(resp)
        self.assertNotIsInstance(ctx.exception, AulaCredentialError)

    def test_404_raises_api_error(self):
        resp = _make_response(404)
        with self.assertRaises(AulaApiError):
            AulaProxyClient._raise_error(resp)

    def test_none_response_noop(self):
        AulaProxyClient._raise_error(None)  # Should not raise

    def test_ok_response_noop(self):
        resp = _make_response(200)
        AulaProxyClient._raise_error(resp)  # Should not raise

    def test_malformed_json_uses_fallback_message(self):
        resp = _make_response(500, text="<html>error</html>")
        resp.json = Mock(side_effect=json.JSONDecodeError("", "", 0))
        with self.assertRaises(AulaApiError) as ctx:
            AulaProxyClient._raise_error(resp)
        self.assertIn("500", str(ctx.exception))


# ---------------------------------------------------------------------------
# _refresh_token data validation
# ---------------------------------------------------------------------------

class TestRefreshTokenValidation(unittest.TestCase):
    """Tests for widget token data type validation in _refresh_token."""

    def setUp(self):
        self.client = AulaProxyClient("test-token")
        self.client._apiurl = "https://example.com/api/v1"

    def test_valid_string_token(self):
        """String JWT data → creates proper AulaToken."""
        resp = _make_response(200, {"data": "some-jwt-token"})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNotNone(token)
        self.assertEqual(token.bearer_token, "Bearer some-jwt-token")

    def test_force_dict_data_raises(self):
        """force=True + dict data → raises AulaApiError (never returns stale garbage)."""
        resp = _make_response(200, {"data": {"error": "expired"}})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

    def test_force_none_data_raises(self):
        """force=True + None data → raises AulaApiError."""
        resp = _make_response(200, {"data": None})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

    def test_force_int_data_raises(self):
        """force=True + integer data → raises AulaApiError."""
        resp = _make_response(200, {"data": 12345})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

    def test_force_http_error_raises(self):
        """force=True + non-200 → raises AulaApiError (never silently returns stale token)."""
        resp = _make_response(500)
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

    def test_force_network_error_raises(self):
        """force=True + network error → raises AulaApiError (never silently returns stale token)."""
        with patch.object(self.client._session, "get", side_effect=RequestsTimeout("timeout")):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

    def test_force_failure_clears_stale_cached_token(self):
        """force=True + failure → removes the stale token from the cache so the next poll starts fresh."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaToken
        from datetime import datetime, timedelta
        import pytz
        stale = AulaToken(bearer_token="Bearer stale", timestamp=datetime.now(pytz.utc) - timedelta(hours=1))
        self.client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = stale

        resp = _make_response(500)
        with patch.object(self.client._session, "get", return_value=resp):
            with self.assertRaises(AulaApiError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertNotIn(AulaWidgetId.WEEKPLAN_PARENTS, self.client._tokens)

    def test_non_force_http_error_returns_old_token(self):
        """force=False + non-200 → returns previously cached token (graceful degradation for non-critical refresh)."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaToken
        from datetime import datetime, timedelta
        import pytz
        # Previous token older than 5 min so non-force attempts a refresh, but not expired
        previous = AulaToken(bearer_token="Bearer prev", timestamp=datetime.now(pytz.utc) - timedelta(minutes=10))
        self.client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = previous

        resp = _make_response(500)
        with patch.object(self.client._session, "get", return_value=resp):
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=False)
        self.assertIs(token, previous)
        self.assertIs(self.client._tokens[AulaWidgetId.WEEKPLAN_PARENTS], previous)

    def test_non_force_network_error_returns_old_token(self):
        """force=False + network error → returns previously cached token (graceful degradation)."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaToken
        from datetime import datetime, timedelta
        import pytz
        previous = AulaToken(bearer_token="Bearer prev", timestamp=datetime.now(pytz.utc) - timedelta(minutes=10))
        self.client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = previous

        with patch.object(self.client._session, "get", side_effect=RequestsTimeout("timeout")):
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=False)
        self.assertIs(token, previous)


# ---------------------------------------------------------------------------
# JWT exp decoding and _get_token cache invalidation
# ---------------------------------------------------------------------------

def _make_jwt(exp_timestamp: int | None) -> str:
    """Build a fake JWT with the given exp claim (or no exp). Signature is dummy."""
    import base64
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b'=').decode()
    claims = {"exp": exp_timestamp} if exp_timestamp is not None else {}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=').decode()
    signature = "dummy"
    return f"{header}.{payload}.{signature}"


class TestJwtExpDecoding(unittest.TestCase):
    """Tests for _decode_jwt_exp and _get_token cache invalidation using JWT exp."""

    def test_decode_valid_jwt_exp(self):
        """Valid JWT with exp claim is decoded to UTC datetime."""
        from custom_components.aula.aula_proxy.aula_proxy_client import _decode_jwt_exp
        import pytz
        from datetime import datetime
        future = int(time.time()) + 3600
        jwt = _make_jwt(future)
        result = _decode_jwt_exp(jwt)
        self.assertIsNotNone(result)
        self.assertEqual(result.tzinfo, pytz.utc)
        self.assertEqual(int(result.timestamp()), future)

    def test_decode_jwt_without_exp_returns_none(self):
        from custom_components.aula.aula_proxy.aula_proxy_client import _decode_jwt_exp
        jwt = _make_jwt(None)
        self.assertIsNone(_decode_jwt_exp(jwt))

    def test_decode_malformed_jwt_returns_none(self):
        from custom_components.aula.aula_proxy.aula_proxy_client import _decode_jwt_exp
        self.assertIsNone(_decode_jwt_exp("not-a-jwt"))
        self.assertIsNone(_decode_jwt_exp("only.two"))
        self.assertIsNone(_decode_jwt_exp(""))

    def test_decode_jwt_exp_in_milliseconds_returns_none(self):
        """Some broken issuers use ms instead of seconds. Reject to avoid caching forever."""
        from custom_components.aula.aula_proxy.aula_proxy_client import _decode_jwt_exp
        ms_timestamp = (int(time.time()) + 3600) * 1000  # ms-encoded
        jwt = _make_jwt(ms_timestamp)
        # ms timestamps would be year ~50000+ — must be rejected
        self.assertIsNone(_decode_jwt_exp(jwt))

    def test_decode_jwt_exp_negative_returns_none(self):
        from custom_components.aula.aula_proxy.aula_proxy_client import _decode_jwt_exp
        self.assertIsNone(_decode_jwt_exp(_make_jwt(-1)))
        self.assertIsNone(_decode_jwt_exp(_make_jwt(0)))

    def test_reset_session_preserves_access_token_and_clears_caches(self):
        """reset_session must drop cookies + widget cache but keep the access_token."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._is_logged_in = True
        client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = AulaToken(
            bearer_token="Bearer cached",
            timestamp=datetime.now(pytz.utc),
            expires_at=datetime.now(pytz.utc) + timedelta(minutes=30),
        )
        # Inject fake cookies
        client._session.cookies.set("Csrfp-Token", "old-csrf")
        client._session.cookies.set("PHPSESSID", "old-phpsess")

        old_session = client._session
        client.reset_session()

        # New session, different object
        self.assertIsNot(client._session, old_session)
        # Access token preserved on new session
        self.assertEqual(client._session._access_token, "test-token")
        # Cookies dropped
        self.assertEqual(len(client._session.cookies), 0)
        # Widget cache cleared
        self.assertNotIn(AulaWidgetId.WEEKPLAN_PARENTS, client._tokens)
        # Logged-in flag reset so next login() re-warms
        self.assertFalse(client._is_logged_in)

    def test_get_token_uses_wallclock_cache_only(self):
        """_get_token uses wall-clock cache only — does NOT validate JWT exp.

        Matches upstream scaarup/aula. Aula occasionally returns JWTs with
        broken exp (negative TTL); the widget endpoint is the authority on
        validity, not us. Validating exp client-side caused regressions.
        """
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        # Cached token has exp 1 second in the past, but timestamp is fresh.
        # Wall-clock cache says "still valid" — we must reuse it.
        cached = AulaToken(
            bearer_token="Bearer cached-but-jwt-expired",
            timestamp=datetime.now(pytz.utc) - timedelta(seconds=10),
            expires_at=datetime.now(pytz.utc) - timedelta(seconds=1),  # JWT-expired
        )
        client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = cached

        with patch.object(client._session, "get") as mock_get:
            result = client._get_token(AulaWidgetId.WEEKPLAN_PARENTS)
        # Returns the cached token despite JWT exp being in the past
        self.assertIs(result, cached)
        mock_get.assert_not_called()

    def test_full_recovery_cookies_oauth_login_widget_token(self):
        """_full_recovery resets cookies, refreshes OAuth, calls login(), fetches new widget JWT.

        Mirrors upstream scaarup/aula PR #341 working approach: drop session
        cookies + force-refresh OAuth access_token + re-warm Aula session +
        fetch fresh widget JWT against the brand-new server session.
        """
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        # Inject some stale cookies that should be dropped by full_recovery
        client._session.cookies.set("Csrfp-Token", "old")
        client._session.cookies.set("PHPSESSID", "old")

        # Set up callback that returns True (OAuth refresh succeeded)
        callback = Mock(return_value=True)
        client.set_token_refresh_callback(callback)

        # Mock login() to succeed without HTTP
        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        with patch.object(AulaProxyClient, "login", return_value=Mock()) as mock_login, \
             patch("custom_components.aula.aula_proxy.aula_proxy_client._TokenSession.get",
                   return_value=_make_response(200, {"data": fresh_jwt})):
            token = client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

        # Verify: callback called (OAuth refresh), login called (re-warm), fresh token returned
        callback.assert_called_once()
        mock_login.assert_called_once()
        self.assertIsNotNone(token)
        self.assertEqual(token.bearer_token, f"Bearer {fresh_jwt}")
        # Cookies were dropped by reset_session() inside full_recovery
        self.assertEqual(len(client._session.cookies), 0)

    def test_full_recovery_propagates_credential_error(self):
        """If OAuth refresh raises AulaCredentialError, _full_recovery propagates it.

        Genuine credential failure must trigger HA reauth — never swallowed.
        """
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"

        # Callback raises AulaCredentialError (refresh_token expired)
        callback = Mock(side_effect=AulaCredentialError("refresh token expired"))
        client.set_token_refresh_callback(callback)

        with self.assertRaises(AulaCredentialError):
            client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

    def test_full_recovery_continues_when_oauth_refresh_returns_false(self):
        """OAuth refresh returning False (transient) should not block recovery."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"

        callback = Mock(return_value=False)  # transient OAuth failure
        client.set_token_refresh_callback(callback)

        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        with patch.object(AulaProxyClient, "login", return_value=Mock()), \
             patch("custom_components.aula.aula_proxy.aula_proxy_client._TokenSession.get",
                   return_value=_make_response(200, {"data": fresh_jwt})):
            with self.assertLogs("custom_components.aula.aula_proxy.aula_proxy_client", level="WARNING") as cm:
                token = client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

        self.assertIsNotNone(token)
        self.assertTrue(any("OAuth access_token refresh returned False" in msg for msg in cm.output))

    def test_is_widget_token_expired_body_detects_expired_message(self):
        """200 OK + {'message': '...expired...'} body must be detected as expired token."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        resp = _make_response(200, {"message": "JWT-Token expired, please renew."})
        self.assertTrue(AulaProxyClient._is_widget_token_expired_body(resp))

    def test_is_widget_token_expired_body_normal_response_returns_false(self):
        """200 OK + valid widget data must NOT be detected as expired."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        resp = _make_response(200, [{"week": "2026-W01", "data": "valid"}])
        self.assertFalse(AulaProxyClient._is_widget_token_expired_body(resp))

    def test_is_widget_token_expired_body_non_200_returns_false(self):
        """401/500 must NOT be classified as 'expired body' — they're handled separately."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        self.assertFalse(AulaProxyClient._is_widget_token_expired_body(_make_response(401, {"message": "expired"})))
        self.assertFalse(AulaProxyClient._is_widget_token_expired_body(_make_response(500)))
        self.assertFalse(AulaProxyClient._is_widget_token_expired_body(None))

    def test_is_widget_token_expired_body_handles_malformed_body(self):
        """Non-JSON or non-dict bodies must not crash."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        resp = Mock(spec=Response)
        resp.status_code = 200
        resp.json = Mock(side_effect=json.JSONDecodeError("", "", 0))
        self.assertFalse(AulaProxyClient._is_widget_token_expired_body(resp))

    def test_full_recovery_cooldown_skips_when_recent(self):
        """Recovery cooldown must prevent OAuth churn during persistent Aula outages."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient, RECOVERY_COOLDOWN
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        # Simulate recent recovery
        client._last_recovery_at = datetime.now(pytz.utc) - timedelta(seconds=30)
        # Seed a stale token
        stale_token = AulaToken(
            bearer_token="Bearer stale",
            timestamp=datetime.now(pytz.utc),
            expires_at=None,
        )
        client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = stale_token

        callback = Mock(return_value=True)
        client.set_token_refresh_callback(callback)

        with self.assertLogs("custom_components.aula.aula_proxy.aula_proxy_client", level="WARNING") as cm:
            result = client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

        # Cooldown skipped recovery — returns the cached token
        self.assertIs(result, stale_token)
        # Callback was NOT called (no OAuth churn)
        callback.assert_not_called()
        # Loud warning about skipping
        self.assertTrue(any("Skipping full recovery" in msg for msg in cm.output))

    def test_full_recovery_cooldown_allows_after_window(self):
        """After cooldown window, recovery proceeds normally."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient, RECOVERY_COOLDOWN
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        # Last recovery older than cooldown
        client._last_recovery_at = datetime.now(pytz.utc) - RECOVERY_COOLDOWN - timedelta(seconds=10)
        client.set_token_refresh_callback(Mock(return_value=True))

        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        with patch.object(AulaProxyClient, "login", return_value=Mock()), \
             patch("custom_components.aula.aula_proxy.aula_proxy_client._TokenSession.get",
                   return_value=_make_response(200, {"data": fresh_jwt})):
            token = client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

        self.assertIsNotNone(token)
        # _last_recovery_at was updated to now
        now = datetime.now(pytz.utc)
        self.assertLess((now - client._last_recovery_at).total_seconds(), 5)

    def test_reset_session_clears_login_result(self):
        """reset_session must clear _login_result so next login() does FULL bootstrap."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaLoginData

        client = AulaProxyClient("test-token")
        client._login_result = AulaLoginData(api_version=19, profiles=[], widgets=[])
        client._is_logged_in = True

        client.reset_session()

        self.assertIsNone(client._login_result)
        self.assertFalse(client._is_logged_in)

    def test_full_recovery_concurrent_calls_serialized(self):
        """Two concurrent _full_recovery calls must serialize via _token_refresh_lock.

        Without locking, both threads would do session reset + OAuth refresh + login
        in parallel — wasted work and potential race conditions.
        """
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        callback_count = 0
        callback_lock = threading.Lock()

        def slow_callback():
            nonlocal callback_count
            with callback_lock:
                callback_count += 1
            time.sleep(0.05)
            return True
        client.set_token_refresh_callback(slow_callback)

        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        with patch.object(AulaProxyClient, "login", return_value=Mock()), \
             patch("custom_components.aula.aula_proxy.aula_proxy_client._TokenSession.get",
                   return_value=_make_response(200, {"data": fresh_jwt})):

            def run():
                client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

            t1 = threading.Thread(target=run)
            t2 = threading.Thread(target=run)
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)

        # Second thread sees the cooldown set by the first → only one OAuth call happens
        self.assertEqual(callback_count, 1)

    def test_full_recovery_continues_when_login_fails(self):
        """If login() fails after reset, still try to fetch widget JWT."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"

        client.set_token_refresh_callback(Mock(return_value=True))

        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        with patch.object(AulaProxyClient, "login", side_effect=ConnectionError("network")), \
             patch("custom_components.aula.aula_proxy.aula_proxy_client._TokenSession.get",
                   return_value=_make_response(200, {"data": fresh_jwt})):
            with self.assertLogs("custom_components.aula.aula_proxy.aula_proxy_client", level="WARNING") as cm:
                token = client._full_recovery(AulaWidgetId.WEEKPLAN_PARENTS)

        # Recovery still produced a token despite login failure
        self.assertIsNotNone(token)
        self.assertTrue(any("login() after session reset failed" in msg for msg in cm.output))

    def test_get_token_race_with_concurrent_clear_does_not_keyerror(self):
        """_get_token must use dict.get() so it doesn't KeyError if another thread
        clears self._tokens between the membership check and the dict access.

        This race exists because reset_session() (called from _refresh_token_locked
        on Thread A) calls self._tokens.clear() while Thread B may be in _get_token.
        The fix is to use dict.get() — a single atomic operation under the GIL.
        """
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"

        # Simulate the race: a dict-like that yields control between __contains__ and __getitem__
        class YieldingDict(dict):
            def __contains__(self, key):
                result = super().__contains__(key)
                # Simulate context switch — another thread clears the dict here
                client._tokens.clear() if isinstance(client._tokens, dict) and not isinstance(client._tokens, YieldingDict) else None
                return result

        # Pre-seed a token, then replace _tokens with the yielding dict
        valid_token = AulaToken(
            bearer_token="Bearer test",
            timestamp=datetime.now(pytz.utc),
            expires_at=datetime.now(pytz.utc) + timedelta(hours=1),
        )

        # Patch _refresh_token to short-circuit (we don't want HTTP)
        with patch.object(client, "_refresh_token", return_value=None):
            # Race: _tokens is cleared between any check-then-access pattern
            # With the dict.get() fix, this should NOT raise KeyError.
            errors = []
            for _ in range(100):
                client._tokens = {AulaWidgetId.WEEKPLAN_PARENTS: valid_token}
                # Simulate concurrent clear by calling between get_token operations
                try:
                    client._get_token(AulaWidgetId.WEEKPLAN_PARENTS)
                    # Now clear simulating Thread A's reset_session
                    client._tokens.clear()
                    client._get_token(AulaWidgetId.WEEKPLAN_PARENTS)
                except KeyError as e:
                    errors.append(e)
            self.assertEqual(len(errors), 0, f"Expected 0 KeyErrors, got {len(errors)}: {errors[:3]}")

    def test_concurrent_refresh_serialized_by_lock(self):
        """Two threads calling _refresh_token concurrently → only one HTTP call thanks to lock + double-check."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"

        new_jwt = _make_jwt(int(time.time()) + 3600)
        call_count = 0
        call_lock = threading.Lock()

        def slow_get(*args, **kwargs):
            nonlocal call_count
            with call_lock:
                call_count += 1
            # simulate network latency
            time.sleep(0.05)
            return _make_response(200, {"data": new_jwt})

        with patch.object(client._session, "get", side_effect=slow_get):
            results = []
            errors = []

            def run():
                try:
                    results.append(client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=False))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=run) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        self.assertEqual(len(results), 3)
        # All threads should get the same token (only one HTTP call thanks to double-check)
        self.assertTrue(all(r is not None for r in results))
        self.assertTrue(all(r.bearer_token == results[0].bearer_token for r in results))
        # Ideally call_count == 1; allow up to 1 due to the double-check pattern
        self.assertEqual(call_count, 1, "Lock + double-check should serialize to a single HTTP refresh")

    def test_get_token_uses_wallclock_cache_within_window(self):
        """Cache is used while within TOKEN_EXPIRATION_TIME wall-clock window."""
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        # 2 min old — well within the 5-min cache window
        cached = AulaToken(
            bearer_token="Bearer cached",
            timestamp=datetime.now(pytz.utc) - timedelta(minutes=2),
            expires_at=None,
        )
        client._tokens[AulaWidgetId.WEEKPLAN_PARENTS] = cached

        with patch.object(client._session, "get") as mock_get:
            result = client._get_token(AulaWidgetId.WEEKPLAN_PARENTS)
        self.assertIs(result, cached)
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# getAulaToken retry behavior (transient 5xx, network errors, main-session 401)
# ---------------------------------------------------------------------------

class TestGetAulaTokenRetry(unittest.TestCase):
    """Tests that _refresh_token absorbs transient failures of the aulaToken endpoint.

    Without these retries, a single 500 or network blip on Aula's token endpoint
    would either silently return a stale token (non-force) or raise AulaApiError
    (force) — both unnecessary given the failure is usually sub-second.
    """

    def setUp(self):
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        self.client = AulaProxyClient("test-token")
        self.client._apiurl = "https://example.com/api/v1"

    def test_transient_5xx_recovers_via_retry(self):
        """500 on first attempt, 200 on second → returns fresh token, no error."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        jwt = _make_jwt(int(time.time()) + 3600)
        responses = iter([
            _make_response(500, text="transient"),
            _make_response(200, {"data": jwt}),
        ])
        with patch.object(self.client._session, "get", side_effect=lambda *a, **kw: next(responses)):
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNotNone(token)
        self.assertEqual(token.bearer_token, f"Bearer {jwt}")

    def test_transient_timeout_recovers_via_retry(self):
        """Timeout on first attempt, 200 on second → returns fresh token."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        jwt = _make_jwt(int(time.time()) + 3600)
        calls = {"n": 0}
        def side_effect(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RequestsTimeout("first attempt times out")
            return _make_response(200, {"data": jwt})
        with patch.object(self.client._session, "get", side_effect=side_effect):
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNotNone(token)
        self.assertEqual(token.bearer_token, f"Bearer {jwt}")

    def test_persistent_5xx_exhausts_retries_and_raises_in_force_mode(self):
        """All attempts 500 → force-mode raises with diagnostic HTTP status."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        with patch.object(self.client._session, "get", return_value=_make_response(500, text="down")):
            with self.assertRaises(AulaApiError) as ctx:
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIn("500", str(ctx.exception))

    def test_main_session_401_triggers_callback_and_retries(self):
        """401 from getAulaToken → token-refresh-callback invoked → retry succeeds on fresh session."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        jwt = _make_jwt(int(time.time()) + 3600)
        callback_called = {"n": 0}
        def callback():
            callback_called["n"] += 1
            return True
        self.client.set_token_refresh_callback(callback)

        # Pattern: all retry attempts return 401 (5xx-retry doesn't help for 401),
        # then _retry_on_401 invokes callback and re-calls session.get → 200.
        call_n = {"n": 0}
        def side_effect(*a, **kw):
            call_n["n"] += 1
            # First REQUEST_MAX_ATTEMPTS attempts hit the retry loop with 401
            # After _retry_on_401 invokes callback, the lambda retries → return 200
            if callback_called["n"] == 0:
                return _make_response(401, text="main session expired")
            return _make_response(200, {"data": jwt})

        with patch.object(self.client._session, "get", side_effect=side_effect):
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)

        self.assertIsNotNone(token)
        self.assertEqual(token.bearer_token, f"Bearer {jwt}")
        self.assertEqual(callback_called["n"], 1, "main-session refresh callback must have been invoked")

    def test_main_session_401_without_callback_fails_in_force_mode(self):
        """No callback set + 401 → force-mode raises (retry does not rescue)."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        # No callback set on client — _retry_on_401 passes 401 through unchanged
        with patch.object(self.client._session, "get", return_value=_make_response(401, text="expired")):
            with self.assertRaises(AulaApiError) as ctx:
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIn("401", str(ctx.exception))

    def test_credential_error_from_callback_propagates(self):
        """If main-session refresh raises AulaCredentialError, propagate for reauth."""
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        def callback():
            raise AulaCredentialError("refresh token expired")
        self.client.set_token_refresh_callback(callback)

        with patch.object(self.client._session, "get", return_value=_make_response(401, text="expired")):
            with self.assertRaises(AulaCredentialError):
                self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)


# ---------------------------------------------------------------------------
# End-to-end widget recovery cycle (integration-level)
# ---------------------------------------------------------------------------

class TestWidgetRecoveryCycle(unittest.TestCase):
    """End-to-end recovery: widget 401 → force-refresh fails → cache cleared → next poll succeeds.

    Protects the multi-step recovery chain against future refactors. If any link
    breaks (e.g. AulaApiError swallowed inside a widget method, stale token not
    cleared on force-refresh failure, _get_token fails to re-fetch on empty cache),
    this test fails — which matches the exact user-reported symptom from issue #2.
    """

    def _make_client_with_widget(self):
        from custom_components.aula.aula_proxy.aula_proxy_client import AulaProxyClient
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaLoginData, AulaWidget
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        client = AulaProxyClient("test-token")
        client._apiurl = "https://example.com/api/v1"
        client._login_result = AulaLoginData(
            api_version=19,
            profiles=[],
            widgets=[AulaWidget(id=1, name="Meebook", widget_id=AulaWidgetId.WEEKPLAN_PARENTS)],
        )
        return client

    def _make_child(self):
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaChildProfile
        return AulaChildProfile(
            first_name="Test",
            id=1,
            institution_code="INST01",
            institution_profile=Mock(),
            main_group=Mock(),
            name="Test Child",
            profile_id=10,
            short_name="T",
            user_id="42",
        )

    def test_full_recovery_cycle_through_get_weekly_plans(self):
        """Poll 1 fails with server-side cascade; Poll 2 succeeds on a clean cache."""
        from custom_components.aula.aula_proxy.aula_errors import AulaApiError
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaToken
        from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
        from datetime import datetime, timedelta
        import pytz

        client = self._make_client_with_widget()
        child = self._make_child()
        widgetid = AulaWidgetId.WEEKPLAN_PARENTS

        # Seed a cached token that the widget will reject (simulates pre-existing state)
        cached = AulaToken(
            bearer_token="Bearer cached",
            timestamp=datetime.now(pytz.utc) - timedelta(minutes=10),
            expires_at=datetime.now(pytz.utc) + timedelta(minutes=30),  # JWT still valid locally
        )
        client._tokens[widgetid] = cached

        # Dates within a single week → one loop iteration
        from_dt = datetime(2026, 4, 1, 12, 0, tzinfo=pytz.utc)
        to_dt = datetime(2026, 4, 3, 12, 0, tzinfo=pytz.utc)

        # Phase 1: widget rejects token → getAulaToken also fails → cascade
        def phase1_response(url, *args, **kwargs):
            if "aulaToken.getAulaToken" in url:
                return _make_response(500, text="Aula token endpoint down")
            return _make_response(401, text='{"message":"JWT-Token expired, please renew."}')

        with patch.object(client._session, "get", side_effect=phase1_response):
            with self.assertRaises(AulaApiError) as ctx:
                client.get_weekly_plans([child], from_dt, to_dt)

        # The error message must be diagnostic enough to pinpoint the cause next time
        err_msg = str(ctx.exception)
        self.assertIn("0004", err_msg, "widget id must be in the error")
        self.assertIn("500", err_msg, "HTTP status must be in the error")
        self.assertIn("aulaToken.getAulaToken", err_msg,
                      "failing endpoint must be identified in the error")

        # Critical invariant: stale cache MUST be cleared so next poll can recover
        self.assertNotIn(widgetid, client._tokens,
                         "stale token must be evicted on force-refresh failure")

        # Phase 2: simulate next poll — Aula endpoint recovered, widget returns data.
        # Real coordinator polls always call login() first, which re-establishes
        # _login_result (cleared by phase 1's reset_session).
        from custom_components.aula.aula_proxy.models.aula_profile_models import AulaLoginData, AulaWidget
        client._login_result = AulaLoginData(
            api_version=19,
            profiles=[],
            widgets=[AulaWidget(id=1, name="Meebook", widget_id=AulaWidgetId.WEEKPLAN_PARENTS)],
        )
        client._is_logged_in = True

        fresh_jwt = _make_jwt(int(time.time()) + 3600)
        def phase2_response(url, *args, **kwargs):
            if "aulaToken.getAulaToken" in url:
                return _make_response(200, {"data": fresh_jwt})
            return _make_response(200, [])  # empty weekly plans list — no fixture needed

        with patch.object(client._session, "get", side_effect=phase2_response):
            plans = client.get_weekly_plans([child], from_dt, to_dt)

        # Cache is repopulated with the fresh token (with decoded JWT exp)
        self.assertIn(widgetid, client._tokens)
        stored = client._tokens[widgetid]
        self.assertEqual(stored.bearer_token, f"Bearer {fresh_jwt}")
        self.assertIsNotNone(stored.expires_at,
                             "fresh token must have a decoded JWT exp")
        # Widget call succeeded — empty list is valid (no plans for this week)
        self.assertEqual(plans, [])


# ---------------------------------------------------------------------------
# _ensure_valid_token and _force_refresh_access_token
# ---------------------------------------------------------------------------

class TestEnsureValidToken(unittest.TestCase):
    """Tests for AulaClient._ensure_valid_token and _force_refresh_access_token."""

    def _make_client(self, expires_at: float = 0, refresh_token: str = "test-refresh"):
        from custom_components.aula.aula_client import AulaClient
        login_client = Mock()
        login_client.tokens = {}
        client = AulaClient(
            access_token="test-access",
            refresh_token=refresh_token,
            expires_at=expires_at,
            mitid_username="test-user",
            login_client=login_client,
            token_update_callback=Mock(),
        )
        return client, login_client

    def test_token_still_valid_no_refresh(self):
        """Token not expired → no refresh call."""
        client, login_client = self._make_client(expires_at=time.time() + 600)
        client._ensure_valid_token()
        login_client.renew_access_token.assert_not_called()

    def test_expired_token_successful_refresh(self):
        """Token expired → refresh succeeds → state updated."""
        client, login_client = self._make_client(expires_at=0)

        def renew_side_effect():
            # Simulate the login client updating its tokens dict on success
            login_client.tokens.update({
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_at": time.time() + 3600,
            })
            return True
        login_client.renew_access_token.side_effect = renew_side_effect

        client._ensure_valid_token()

        self.assertEqual(client._access_token, "new-access")
        self.assertEqual(client._refresh_token, "new-refresh")

    def test_no_refresh_token_raises_credential_error(self):
        """No refresh token → MUST raise AulaCredentialError (legitimate reauth)."""
        client, _ = self._make_client(expires_at=0, refresh_token="")

        with self.assertRaises(AulaCredentialError):
            client._ensure_valid_token()

    def test_token_expired_error_raises_credential_error(self):
        """TokenExpiredError from server → MUST raise AulaCredentialError."""
        from custom_components.aula.aula_login_client.exceptions import TokenExpiredError
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.side_effect = TokenExpiredError("expired")

        with self.assertRaises(AulaCredentialError):
            client._ensure_valid_token()

    def test_network_error_raises_connection_error_not_credential(self):
        """NetworkError → ConnectionError, NOT AulaCredentialError (no reauth)."""
        from custom_components.aula.aula_login_client.exceptions import NetworkError
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.side_effect = NetworkError("network down")

        with self.assertRaises(ConnectionError):
            client._ensure_valid_token()
        # Verify it's not a credential error
        try:
            client._expires_at = 0
            client._ensure_valid_token()
        except AulaCredentialError:
            self.fail("NetworkError must NOT raise AulaCredentialError")
        except ConnectionError:
            pass  # Expected

    def test_renew_returns_false_raises_connection_error_not_credential(self):
        """renew_access_token() returns False → ConnectionError, NOT AulaCredentialError."""
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.return_value = False

        with self.assertRaises(ConnectionError):
            client._ensure_valid_token()
        # Verify it's not a credential error
        try:
            client._expires_at = 0
            client._ensure_valid_token()
        except AulaCredentialError:
            self.fail("False return must NOT raise AulaCredentialError")
        except ConnectionError:
            pass  # Expected

    def test_force_refresh_success(self):
        """_force_refresh_access_token returns True on successful refresh."""
        client, login_client = self._make_client(expires_at=time.time() + 600)
        login_client.renew_access_token.return_value = True
        login_client.tokens = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_at": time.time() + 3600,
        }

        result = client._force_refresh_access_token()

        self.assertTrue(result)

    def test_force_refresh_transient_failure_returns_false(self):
        """_force_refresh_access_token returns False on transient failure (ConnectionError)."""
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.return_value = False

        result = client._force_refresh_access_token()

        self.assertFalse(result)

    def test_force_refresh_credential_error_propagates(self):
        """_force_refresh_access_token lets AulaCredentialError propagate."""
        from custom_components.aula.aula_login_client.exceptions import TokenExpiredError
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.side_effect = TokenExpiredError("expired")

        with self.assertRaises(AulaCredentialError):
            client._force_refresh_access_token()

    def test_force_refresh_unexpected_exception_returns_false(self):
        """_force_refresh_access_token catches unexpected (non-credential) exceptions."""
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.side_effect = RuntimeError("unexpected")

        result = client._force_refresh_access_token()

        self.assertFalse(result)

    def test_thread_safety_concurrent_refresh(self):
        """Two threads calling _ensure_valid_token → renew called exactly once."""
        client, login_client = self._make_client(expires_at=0)
        call_count = 0

        def slow_renew():
            nonlocal call_count
            call_count += 1
            # Simulate some work
            login_client.tokens = {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_at": time.time() + 3600,
            }
            return True

        login_client.renew_access_token.side_effect = slow_renew

        threads = []
        errors = []
        for _ in range(2):
            def run():
                try:
                    client._ensure_valid_token()
                except Exception as e:
                    errors.append(e)
            t = threading.Thread(target=run)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        # Due to double-checked locking, renew should be called once
        # (the second thread sees the updated _expires_at)
        self.assertEqual(call_count, 1)


if __name__ == "__main__":
    unittest.main()
