"""
Based on https://github.com/JBoye/HA-Aula
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
import logging

from .aula_data import AulaHassData, remove_hass_data, set_hass_data
from .aula_coordinator import AulaCoordinator
from .aula_client import AulaClient
from .const import DOMAIN, STARTUP

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    # Platform.CLIMATE,
    # Platform.SWITCH,
    # Platform.NUMBER,
    # Platform.BUTTON,
    # Platform.SELECT,
]
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})

    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)
    _LOGGER.debug(entry.data)

    username = str(entry.data.get(CONF_USERNAME))
    password = str(entry.data.get(CONF_PASSWORD))
    client = AulaClient(username, password)
    coordinator = AulaCoordinator(entry.title, hass, client)
    hass_data: AulaHassData = {
        "username": username,
        "password": password,
        "client": client,
        "coordinator": coordinator,
    }

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    await coordinator.async_config_entry_first_refresh()

    set_hass_data(hass, entry, hass_data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entry when its updated.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # the following line invokes the async_unload_entry method, followed by async_setup_entry
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    success = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not success: return False
    remove_hass_data(hass, entry)
    return True