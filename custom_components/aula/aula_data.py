

from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .aula_calendar_coordinator import AulaCalendarCoordinator
from .aula_client import AulaClient
from .aula_data_coordinator import AulaDataCoordinator
from .const import DOMAIN # type: ignore

class AulaHassData(TypedDict):
    client: AulaClient
    data_coordinator: AulaDataCoordinator
    calendar_coordinator: AulaCalendarCoordinator
    username: str
    password: str

def get_hass_data(hass: HomeAssistant, entry: ConfigEntry) -> AulaHassData:
    return hass.data[DOMAIN][entry.entry_id]

def get_aula_client(hass: HomeAssistant, entry: ConfigEntry) -> AulaClient:
    data = get_hass_data(hass, entry)
    return data["client"]

def get_aula_data_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> AulaDataCoordinator:
    data = get_hass_data(hass, entry)
    return data["data_coordinator"]

def get_aula_calendar_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> AulaCalendarCoordinator:
    data = get_hass_data(hass, entry)
    return data["calendar_coordinator"]

def remove_hass_data(hass: HomeAssistant, entry: ConfigEntry) -> AulaHassData:
    return hass.data[DOMAIN].pop(entry.entry_id)

def set_hass_data(hass: HomeAssistant, entry: ConfigEntry, data:AulaHassData) -> None:
    hass.data[DOMAIN][entry.entry_id] = data
