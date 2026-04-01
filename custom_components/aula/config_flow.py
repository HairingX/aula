import asyncio
import concurrent.futures
import logging
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, SOURCE_RECONFIGURE
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .aula_login_client.client import AulaLoginClient
from homeassistant.const import CONF_ID
from .const import (
    AUTH_METHOD_APP,
    AUTH_METHOD_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_AUTH_METHOD,
    CONF_MITID_USERNAME,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
)
from .views import AulaAuthView, AulaAuthStatusView, AulaAuthSelectIdentityView

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID, default="Aula"): cv.string,
        vol.Required(CONF_MITID_USERNAME): cv.string,
        vol.Optional("mitid_use_token", default=False): cv.boolean,
    }
)

TOKEN_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required("mitid_password"): cv.string,
        vol.Required("mitid_token"): cv.string,
    }
)


class AulaCustomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Aula config flow with MitID authentication."""

    VERSION = 2

    def __init__(self):
        self._entry_id: str = "Aula"
        self._mitid_username: str | None = None
        self._auth_method: str | None = None
        self._mitid_password: str | None = None
        self._mitid_token: str | None = None
        self._auth_client: AulaLoginClient | None = None
        self._tokens: dict | None = None
        self._reauth_entry = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            self._entry_id = user_input.get(CONF_ID, "Aula").strip()
            use_token = user_input.get("mitid_use_token", False)
            self._mitid_username = user_input[CONF_MITID_USERNAME]
            self._auth_method = AUTH_METHOD_TOKEN if use_token else AUTH_METHOD_APP

            if not self._entry_id:
                return self.async_show_form(
                    step_id="user", data_schema=USER_SCHEMA, errors={"base": "invalid_id"}
                )

            existing = await self.async_set_unique_id(self._entry_id)
            if existing:
                return self.async_show_form(
                    step_id="user", data_schema=USER_SCHEMA, errors={"base": "id_already_in_use"}
                )

            if use_token:
                return await self.async_step_token_credentials()
            return await self.async_step_authenticate()

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_token_credentials(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            self._mitid_password = user_input["mitid_password"]
            self._mitid_token = user_input["mitid_token"]
            return await self.async_step_authenticate()

        return self.async_show_form(
            step_id="token_credentials",
            data_schema=TOKEN_CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def async_step_authenticate(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """MitID authentication with external step (QR code display in browser)."""
        # Check for existing session
        session_data = None
        if (
            DOMAIN in self.hass.data
            and "auth_sessions" in self.hass.data.get(DOMAIN, {})
            and self.flow_id in self.hass.data[DOMAIN]["auth_sessions"]
        ):
            session_data = self.hass.data[DOMAIN]["auth_sessions"][self.flow_id]

        # Start or restart auth
        should_start = session_data is None or (
            user_input is not None and session_data.get("error")
        )

        if should_start:
            self.hass.data.setdefault(DOMAIN, {})
            self.hass.data[DOMAIN].setdefault("auth_sessions", {})

            # Register views (safe to call multiple times — HA deduplicates)
            self.hass.http.register_view(AulaAuthView(self.hass))
            self.hass.http.register_view(AulaAuthStatusView(self.hass))
            self.hass.http.register_view(AulaAuthSelectIdentityView(self.hass))

            self._auth_client = AulaLoginClient(
                mitid_username=self._mitid_username,
                mitid_password=self._mitid_password,
                mitid_token=self._mitid_token,
                auth_method=self._auth_method,
            )

            session_data = {
                "client": self._auth_client,
                "status_message": "Open your MitID app now...",
                "completed": False,
                "error": None,
                "identity_future": None,
                "available_identities": None,
            }
            self.hass.data[DOMAIN]["auth_sessions"][self.flow_id] = session_data

            # Wire identity selection callback for multi-company users
            def identity_selector(identities):
                session_data["available_identities"] = identities
                session_data["status_message"] = "Please select an identity"
                future = concurrent.futures.Future()
                session_data["identity_future"] = future
                try:
                    return future.result(timeout=300)
                except Exception as e:
                    _LOGGER.error("Identity selection timed out or failed: %s", e)
                    raise

            self._auth_client.identity_selector = identity_selector

            # Start background auth task
            self.hass.async_create_task(self._authenticate_async(session_data))

            return self.async_external_step(
                step_id="authenticate",
                url=f"/api/aula/auth/{self.flow_id}",
            )

        # Auth completed successfully
        if session_data.get("completed"):
            self._tokens = session_data.get("tokens")
            if not self._tokens:
                _LOGGER.error("Tokens not found in completed session")
                return self.async_external_step_done(next_step_id="auth_error")

            # Schedule cleanup
            self.hass.async_create_task(self._delayed_cleanup(self.flow_id))
            return self.async_external_step_done(next_step_id="complete")

        # Auth failed
        if session_data.get("error"):
            return self.async_external_step_done(next_step_id="auth_error")

        # Still in progress — keep showing external step
        return self.async_external_step(
            step_id="authenticate",
            url=f"/api/aula/auth/{self.flow_id}",
        )

    async def async_step_complete(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Create or update config entry with tokens."""
        data = {
            CONF_MITID_USERNAME: self._mitid_username,
            CONF_AUTH_METHOD: self._auth_method,
            CONF_ACCESS_TOKEN: self._tokens.get("access_token", ""),
            CONF_REFRESH_TOKEN: self._tokens.get("refresh_token", ""),
            CONF_TOKEN_EXPIRES_AT: self._tokens.get("expires_at", 0),
        }

        if self._reauth_entry:
            return self.async_update_reload_and_abort(
                self._reauth_entry,
                data=data,
            )

        return self.async_create_entry(
            title=self._entry_id, data=data
        )

    async def async_step_auth_error(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Display error and allow retry."""
        if user_input is not None:
            # TOKEN method: send back to credentials form for fresh one-time code
            if self._auth_method == AUTH_METHOD_TOKEN:
                return await self.async_step_token_credentials()
            return await self.async_step_authenticate(user_input)

        return self.async_show_form(
            step_id="auth_error",
            errors={"base": "auth_failed"},
        )

    async def _authenticate_async(self, session_data: dict) -> None:
        """Background authentication task."""
        try:
            _LOGGER.info(
                "Starting MitID authentication for %s using %s",
                self._mitid_username,
                self._auth_client.auth_method,
            )

            # Monitor BrowserClient status messages
            monitor_task = self.hass.async_create_task(
                self._monitor_client_status(session_data)
            )

            # Run blocking authenticate() in executor
            result = await self.hass.async_add_executor_job(
                self._auth_client.authenticate
            )

            monitor_task.cancel()

            if result.get("success"):
                session_data["tokens"] = result.get("tokens")
                session_data["completed"] = True
                session_data["status_message"] = "Authentication successful!"
                _LOGGER.info("MitID authentication successful")
            else:
                error_msg = result.get("error", "Unknown error")
                session_data["error"] = error_msg
                _LOGGER.error("MitID authentication failed: %s", error_msg)

        except Exception as err:
            _LOGGER.error("MitID authentication error: %s", err)
            session_data["error"] = str(err)

        # Re-enter the flow to advance past external step
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def _monitor_client_status(self, session_data: dict) -> None:
        """Monitor BrowserClient status_message and update session."""
        client = session_data["client"]
        while True:
            try:
                mitid_client = client.get_mitid_client()
                if mitid_client and hasattr(mitid_client, "status_message"):
                    if not session_data.get("available_identities"):
                        session_data["status_message"] = mitid_client.status_message
            except Exception:
                pass
            await asyncio.sleep(1)

    def async_remove(self) -> None:
        """Called by HA when the flow is removed (timeout, user navigated away, etc.)."""
        self._cleanup_session(self.flow_id)

    def _cleanup_session(self, flow_id: str) -> None:
        """Remove auth session data immediately."""
        if (
            DOMAIN in self.hass.data
            and "auth_sessions" in self.hass.data.get(DOMAIN, {})
        ):
            self.hass.data[DOMAIN]["auth_sessions"].pop(flow_id, None)

    async def _delayed_cleanup(self, flow_id: str) -> None:
        """Clean up auth session data after a delay (for successful flows)."""
        await asyncio.sleep(60)
        self._cleanup_session(flow_id)

    # --- Reauth ---

    async def async_step_reauth(
        self, entry_data: dict
    ) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._mitid_username = self._reauth_entry.data.get(CONF_MITID_USERNAME, "")
        self._auth_method = self._reauth_entry.data.get(
            CONF_AUTH_METHOD, AUTH_METHOD_APP
        )
        self._mitid_password = None
        self._mitid_token = None

        # If no MitID username stored (v1→v2 migration), ask for it
        if not self._mitid_username:
            return await self.async_step_reauth_username()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_username(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Ask for MitID username when migrating from UniLogin."""
        if user_input is not None:
            self._mitid_username = user_input[CONF_MITID_USERNAME].strip()
            if not self._mitid_username:
                return self.async_show_form(
                    step_id="reauth_username",
                    data_schema=vol.Schema(
                        {vol.Required(CONF_MITID_USERNAME): cv.string}
                    ),
                    errors={"base": "invalid_auth"},
                )
            return await self.async_step_reauth_confirm()

        return self.async_show_form(
            step_id="reauth_username",
            data_schema=vol.Schema(
                {vol.Required(CONF_MITID_USERNAME): cv.string}
            ),
        )

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Clear stale session
            if (
                DOMAIN in self.hass.data
                and "auth_sessions" in self.hass.data.get(DOMAIN, {})
            ):
                self.hass.data[DOMAIN]["auth_sessions"].pop(self.flow_id, None)
            return await self.async_step_authenticate()

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"username": self._mitid_username},
        )

    # --- Reconfigure ---

    async def async_step_reconfigure(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Reconfigure allows changing username and re-authenticating with MitID."""
        entry = self._get_reconfigure_entry()
        self._reauth_entry = entry

        errors: Dict[str, str] = {}
        if user_input is not None:
            use_token = user_input.get("mitid_use_token", False)
            self._mitid_username = user_input[CONF_MITID_USERNAME].strip()
            self._auth_method = AUTH_METHOD_TOKEN if use_token else AUTH_METHOD_APP

            if not self._mitid_username:
                errors["base"] = "invalid_auth"
            else:
                if use_token:
                    return await self.async_step_token_credentials()
                return await self.async_step_authenticate()

        # Pre-fill with existing username if available
        existing_username = entry.data.get(CONF_MITID_USERNAME, "")
        schema = vol.Schema(
            {
                vol.Required(CONF_MITID_USERNAME, default=existing_username): cv.string,
                vol.Optional("mitid_use_token", default=False): cv.boolean,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
