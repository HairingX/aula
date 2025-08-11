import logging
from typing import Any, Dict, Mapping, Optional
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
import voluptuous as vol

from .aula_proxy.aula_errors import AulaCredentialError, ParseError
from .aula_client import AulaClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class AulaCustomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Aula."""

    VERSION = 1
    _id:str = "Aula"
    _username:str = ""
    _password:str = ""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> ConfigFlowResult:
        """Invoked when a user initiates a flow via the user interface."""
        return self.async_show_configure()

    def async_show_configure(self, error: Exception|None = None) -> ConfigFlowResult:
        data_schema = vol.Schema({
            vol.Required(CONF_ID, default=self._id): str,
            vol.Required(CONF_USERNAME, default=self._username): str,
            vol.Required(CONF_PASSWORD, default=self._password): str,
        })
        errors = self._parse_error(error)
        return self.async_show_form(step_id="conf", data_schema=data_schema, errors=errors)

    async def async_step_conf(self, user_input:Dict[str, str]) -> ConfigFlowResult:
        """After user has provided their initial configuration data."""
        self._id = user_input.get(CONF_ID, "").strip()

        #go back if id is invalid or not unique
        if len(self._id.strip()) == 0: return self.async_show_configure(ValueError("invalid_id"))

        config_entry = await self.async_set_unique_id(self._id)
        if config_entry: return self.async_show_configure(ValueError("id_already_in_use"))

        result = await self._async_try_set_username_password(user_input)
        #result is an error
        if isinstance(result, Exception):
            return self.async_show_configure(result)

        #valid data - save data
        _LOGGER.debug(f"logged in: {result}")
        config_data:Mapping[str, Any] = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
        }
        # return self.async_abort(reason="Login success")
        return self.async_create_entry(title=self._id, data=config_data)


    async def async_step_reconfigure(self, user_input:Dict[str, str]) -> ConfigFlowResult:
        """After user has provided their ip, port and email. Try to connect and see if email is correct."""
        #get the persisted data
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if config_entry is None: return self.async_abort(reason="missing_entry_data")
        data = config_entry.data
        #assign self properties from the persisted data
        self._id = data.get(CONF_ID, "")
        self._username = data.get(CONF_USERNAME, "")
        self._password = data.get(CONF_PASSWORD, "")

        return self.async_show_reconfigure()

    async def async_step_reauth(self, user_input:Dict[str, str]) -> ConfigFlowResult:
        """When integration has indicated that reauthentication is needed."""
        #get the persisted data
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if config_entry is None: return self.async_abort(reason="missing_entry_data")
        data = config_entry.data
        #assign self properties from the persisted data
        self._id = data.get(CONF_ID, "")
        self._username = data.get(CONF_USERNAME, "")
        self._password = data.get(CONF_PASSWORD, "")

        return self.async_show_reconfigure()

    def async_show_reconfigure(self, error: Exception|None = None) -> ConfigFlowResult:
        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME, default=self._username): str,
            vol.Required(CONF_PASSWORD, default=self._password): str,
        })
        errors = self._parse_error(error)
        return self.async_show_form(step_id="reconf", data_schema=data_schema, errors=errors)

    async def async_step_reconf(self, user_input:Dict[str, str]) -> ConfigFlowResult:
        """Show the reconfig form."""
        result = await self._async_try_set_username_password(user_input)
        _LOGGER.debug(f"validate result: {result}")
        if isinstance(result, Exception):
            return self.async_show_reconfigure(result)

        #valid data - save data
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if config_entry is None: return self.async_abort(reason="missing_entry_data")
        config_data = config_entry.data.copy()
        config_data[CONF_USERNAME] = self._username
        config_data[CONF_PASSWORD] = self._password

        return self.async_update_reload_and_abort(
            config_entry,
            unique_id=config_entry.unique_id,
            data=config_data,
            reason="success",
        )

    async def _async_try_set_username_password(self, user_input:Dict[str, str]) -> Exception|AulaClient:
        """
        Validate user input, set username and password and attempt to log in to the Aula service.
        Returns:
            (Exception | AulaService): Returns an AulaService instance if login is successful,
            otherwise returns a Exception indicating the reason for aborting.
        """
        self._username = user_input.get(CONF_USERNAME, "").strip()
        self._password = user_input.get(CONF_PASSWORD, "")

        if len(self._username.strip()) == 0: return ValueError("invalid_username")
        if len(self._password) == 0: return ValueError("invalid_password")

        return await self.hass.async_add_executor_job(self._check_connection)


    def _check_connection(self) -> Exception|AulaClient:
        service = AulaClient(self._username, self._password)
        try:
            service.connection_check()
            _LOGGER.debug(f"Successfully logged in")
            return service
        except Exception as ex:
            return ex

    @staticmethod
    def _parse_error(error: Exception|None) -> Dict[str,str] :
        errors:Dict[str,str] = {}
        if error is not None:
            if isinstance(error, AulaCredentialError):
                errors["base"] = "invalid_auth"
            elif isinstance(error, ParseError):
                errors["base"] = "invalid_response"
            elif isinstance(error.args, str):
                errors["base"] = str(error.args)
            else:
                errors["base"] = str(error)

        return errors