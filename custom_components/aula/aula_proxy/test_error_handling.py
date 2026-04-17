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

    def test_callback_returns_false(self):
        """Refresh fails → returns original 401, no retry request made."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=False)
        request_fn = Mock()

        self.client.set_token_refresh_callback(callback)
        result = self.client._retry_on_401(resp_401, request_fn)

        self.assertIs(result, resp_401)
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

    def test_retry_network_error_returns_original(self):
        """If the retry request fails with a network error, return the original 401."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=True)
        request_fn = Mock(side_effect=RequestsConnectionError("conn error"))

        self.client.set_token_refresh_callback(callback)
        result = self.client._retry_on_401(resp_401, request_fn)

        self.assertIs(result, resp_401)

    def test_retry_timeout_returns_original(self):
        """If the retry request times out, return the original 401."""
        resp_401 = _make_response(401)
        callback = Mock(return_value=True)
        request_fn = Mock(side_effect=RequestsTimeout("timeout"))

        self.client.set_token_refresh_callback(callback)
        result = self.client._retry_on_401(resp_401, request_fn)

        self.assertIs(result, resp_401)


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

    def test_dict_data_rejected(self):
        """Dict data (e.g. error payload) → returns old token, not garbage."""
        resp = _make_response(200, {"data": {"error": "expired"}})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        # Should return None (no previous token) rather than garbage
        self.assertIsNone(token)

    def test_none_data_rejected(self):
        """None data → returns old token."""
        resp = _make_response(200, {"data": None})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNone(token)

    def test_int_data_rejected(self):
        """Integer data → returns old token."""
        resp = _make_response(200, {"data": 12345})
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNone(token)

    def test_http_error_returns_old_token(self):
        """Non-200 → returns previous token (None if no previous)."""
        resp = _make_response(500)
        with patch.object(self.client._session, "get", return_value=resp):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNone(token)

    def test_network_error_returns_old_token(self):
        """Network error → returns previous token."""
        with patch.object(self.client._session, "get", side_effect=RequestsTimeout("timeout")):
            from custom_components.aula.aula_proxy.models.constants import AulaWidgetId
            token = self.client._refresh_token(AulaWidgetId.WEEKPLAN_PARENTS, force=True)
        self.assertIsNone(token)


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

    def test_force_refresh_failure_returns_false(self):
        """_force_refresh_access_token returns False on any failure."""
        client, login_client = self._make_client(expires_at=0)
        login_client.renew_access_token.return_value = False

        result = client._force_refresh_access_token()

        self.assertFalse(result)

    def test_force_refresh_unexpected_exception_returns_false(self):
        """_force_refresh_access_token catches unexpected exceptions."""
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
