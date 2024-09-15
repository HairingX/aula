

from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .aula_coordinator import AulaCoordinator
from .aula_client import AulaClient
from .const import DOMAIN # type: ignore

class AulaHassData(TypedDict):
    client: AulaClient
    coordinator: AulaCoordinator
    username: str
    password: str

def get_hass_data(hass: HomeAssistant, entry: ConfigEntry) -> AulaHassData:
    return hass.data[DOMAIN][entry.entry_id]

def get_aula_client(hass: HomeAssistant, entry: ConfigEntry) -> AulaClient:
    data = get_hass_data(hass, entry)
    return data["client"]

def get_aula_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> AulaCoordinator:
    data = get_hass_data(hass, entry)
    return data["coordinator"]

def remove_hass_data(hass: HomeAssistant, entry: ConfigEntry) -> AulaHassData:
    return hass.data[DOMAIN].pop(entry.entry_id)

def set_hass_data(hass: HomeAssistant, entry: ConfigEntry, data:AulaHassData) -> None:
    hass.data[DOMAIN][entry.entry_id] = data
