from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant import config_entries, core
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry, async_add_entities):

    client = hass.data[DOMAIN]["client"]
    if client.unread_messages == 1:
        subject = client.message["subject"]
        text = client.message["text"]
        sender = client.message["sender"]
    else:
        subject = ""
        text = ""

    sensors = []
    device = AulaBinarySensor(hass=hass, unread=client.unread_messages, subject=subject, text=text, sender=sender)
    sensors.append(device)
    async_add_entities(sensors, True)


class AulaBinarySensor(BinarySensorEntity, RestoreEntity):
    def __init__(self,hass,unread,subject,text,sender):
        self._hass = hass
        self._unread = unread
        self._subject = subject
        self._text = text
        self._sender = sender
        self._client = self._hass.data[DOMAIN]["client"]

    @property
    def extra_state_attributes(self):
        attributes = {}
        attributes["subject"] = self._subject
        attributes["text"] = self._text
        attributes["sender"] = self._sender
        attributes["friendly_name"] = "Aula message"
        return attributes

    @property
    def unique_id(self):
        unique_id = "aulamessage"
        return unique_id

    @property
    def icon(self):
        return 'mdi:email'

    @property
    def friendly_name(self):
        return "Aula message"

    @property
    def is_on(self):
        if self._state == 1:
            return True
        if self._state == 0:
            return False

    def update(self):
        if self._client.unread_messages == 1:
            _LOGGER.debug("There are unread message(s)")
            _LOGGER.debug("Latest message: "+str(self._client.message))
            self._subject = self._client.message["subject"]
            self._text = self._client.message["text"]
            self._sender = self._client.message["sender"]
            self._state = 1
        else:
                _LOGGER.debug("There are NO unread messages")
                self._state = 0
                self._subject = ""
                self._text = ""
                self._sender = ""