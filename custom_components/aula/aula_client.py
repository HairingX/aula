from typing import Callable, List
import datetime
import logging
import time
import threading

from .aula_proxy.const import API_VERSION
from .aula_proxy.models.constants import AulaWidgetId
from .aula_proxy.module import (
    AulaBirthdayEvent,
    AulaCalendarEvent,
    AulaDailyOverview,
    AulaEasyiqWeeklyPlan,
    AulaInstitutionProfile,
    AulaLoginData,
    AulaMessageThread,
    AulaProfile,
    AulaProxyClient,
    AulaWeeklyNewsletter,
    AulaWeeklyPlan,
    AulaChildProfile,
    AULA_NOTIFICATION_TYPES,
)
from .aula_proxy.aula_errors import AulaCredentialError
from .aula_login_client import AulaLoginClient
from .aula_login_client.exceptions import NetworkError, TokenExpiredError

_LOGGER = logging.getLogger(__name__)

TOKEN_REFRESH_BUFFER_SECONDS = 300
"""Refresh tokens 5 minutes before expiry."""


class AulaClient:
    aula_version: int = int(API_VERSION)
    _proxy: AulaProxyClient

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: float,
        mitid_username: str,
        login_client: AulaLoginClient,
        token_update_callback: Callable[[str, str, float], None] | None = None,
    ):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at
        self._mitid_username = mitid_username
        self._login_client = login_client
        self._token_update_callback = token_update_callback
        self._token_lock = threading.Lock()
        self._proxy = AulaProxyClient(access_token, username_for_meebook=mitid_username)
        self._proxy.set_token_refresh_callback(self._force_refresh_access_token)

    def close(self) -> None:
        """Close HTTP sessions."""
        self._proxy.close()
        if hasattr(self._login_client, 'session'):
            self._login_client.session.close()

    def connection_check(self) -> None:
        """
        Attempts to log in using the proxy with token-based auth.
        Raises:
            AulaCredentialError: If access to the Aula API is denied.
            ConnectionRefusedError: If the API URL is unreachable.
        """
        self._ensure_valid_token()
        self._proxy.login()
        self.aula_version = self._proxy.api_version

    def has_widget(self, widgetid: AulaWidgetId):
        return self._proxy.has_widget(widgetid)

    def login(self) -> AulaLoginData:
        self._ensure_valid_token()
        return self._proxy.login()

    def _force_refresh_access_token(self) -> bool:
        """Force-refresh the access token, bypassing the expiry check.

        Used as a callback by AulaProxyClient when it receives a 401 from the
        Aula API after the token was already validated — i.e. a transient
        server-side issue.  Returns True on success, False on any failure.
        """
        self._expires_at = 0  # Force the expiry check to trigger a refresh
        try:
            self._ensure_valid_token()
            return True
        except Exception:
            _LOGGER.debug("Forced token refresh failed", exc_info=True)
            return False

    def _ensure_valid_token(self) -> None:
        """Check token expiration and refresh if needed. Thread-safe."""
        if time.time() < self._expires_at - TOKEN_REFRESH_BUFFER_SECONDS:
            return  # Token still valid

        with self._token_lock:
            # Double-check after acquiring lock — another thread may have refreshed
            if time.time() < self._expires_at - TOKEN_REFRESH_BUFFER_SECONDS:
                return

            # Guard: no refresh token means we genuinely need re-authentication
            if not self._refresh_token:
                raise AulaCredentialError("No refresh token available, re-authentication required")

            _LOGGER.debug("Access token expired or expiring soon, attempting refresh")
            self._login_client.tokens = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
            }

            try:
                success = self._login_client.renew_access_token()
            except TokenExpiredError as err:
                # Refresh token permanently invalid — trigger reauth
                raise AulaCredentialError(
                    "Refresh token expired, re-authentication required"
                ) from err
            except (NetworkError, OSError) as err:
                # Transient network failure — don't trigger reauth, let coordinator retry
                _LOGGER.warning("Network error during token refresh: %s", err)
                raise ConnectionError(f"Network error during token refresh: {err}") from err

            if not success:
                # renew_access_token() returns False for transient issues (malformed
                # server response, unexpected HTTP status, generic exceptions) — these
                # are NOT credential rejections and must NOT trigger MitID reauth.
                _LOGGER.warning("Token refresh returned False — treating as transient failure")
                raise ConnectionError("Token refresh failed — server returned an unexpected response")

            # Extract all new values before updating state
            new_access = self._login_client.tokens["access_token"]
            new_refresh = self._login_client.tokens.get(
                "refresh_token", self._refresh_token
            )
            new_expires = self._login_client.tokens.get(
                "expires_at", time.time() + 3600
            )

            # Update in-memory state
            self._access_token = new_access
            self._refresh_token = new_refresh
            self._expires_at = new_expires
            self._proxy.update_token(new_access)

            _LOGGER.debug("Token refreshed successfully, expires at %s", new_expires)

            # Persist tokens (callback uses call_soon_threadsafe)
            if self._token_update_callback:
                self._token_update_callback(new_access, new_refresh, new_expires)

    def get_birthday_events(
        self,
        profiles: List[AulaChildProfile],
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ) -> List[AulaBirthdayEvent]:
        self._ensure_valid_token()
        return self._proxy.get_birthday_events(profiles, start_datetime, end_datetime)

    def get_daily_overviews(
        self, profiles: List[AulaProfile]
    ) -> List[AulaDailyOverview]:
        self._ensure_valid_token()
        return self._proxy.get_daily_overviews(profiles)

    def get_calendar_events(
        self,
        profiles: List[AulaInstitutionProfile],
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ) -> List[AulaCalendarEvent]:
        self._ensure_valid_token()
        return self._proxy.get_calendar_events(profiles, start_datetime, end_datetime)

    def get_message_threads(self) -> List[AulaMessageThread]:
        self._ensure_valid_token()
        return self._proxy.get_message_threads()

    def get_notifications(
        self, profiles: List[AulaChildProfile]
    ) -> List[AULA_NOTIFICATION_TYPES]:
        self._ensure_valid_token()
        return self._proxy.get_notifications(profiles)

    def get_weekly_plans(
        self,
        profiles: List[AulaChildProfile],
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ) -> List[AulaWeeklyPlan]:
        self._ensure_valid_token()
        return self._proxy.get_weekly_plans(profiles, start_datetime, end_datetime)

    def get_easyiq_weekly_plans(
        self,
        profiles: List[AulaChildProfile],
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ) -> List[AulaEasyiqWeeklyPlan]:
        self._ensure_valid_token()
        return self._proxy.get_easyiq_weekly_plans(
            profiles, start_datetime, end_datetime
        )

    def get_newsletters(
        self,
        profiles: List[AulaChildProfile],
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ) -> List[AulaWeeklyNewsletter]:
        self._ensure_valid_token()
        return self._proxy.get_newsletters(profiles, start_datetime, end_datetime)
