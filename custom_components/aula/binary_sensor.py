from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Any, List
import logging

from .entity import AulaEntityBase
from .aula_coordinator import AulaCoordinator, AulaCoordinatorData
from .aula_data import get_aula_coordinator
from .aula_proxy.models.aula_message_thread_models import AulaMessageThread

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup binary sensors from a config entry created in the integrations UI."""
    coordinator = get_aula_coordinator(hass, entry)
    entities: List[BinarySensorEntity] = []
    entities.append(AulaUnreadMessageBinarySensor(coordinator))
    async_add_entities(entities)

class AulaUnreadMessageBinarySensor(AulaEntityBase[None], BinarySensorEntity): # type: ignore
    def __init__(self, coordinator: AulaCoordinator):
        super().__init__(coordinator, name="unread_message", context=None)
        self._init_data()

    def _set_values(self, data: AulaCoordinatorData, context:None) -> None:
        self._attr_is_on = False
        threads = self.coordinator.data["message_threads"]
        unread_thread: AulaMessageThread|None = None
        for thread in threads:
            if not thread["read"]:
                unread_thread = thread

        self._attr_is_on = unread_thread is not None
        self._attr_icon = 'mdi:email'
        attributes = dict[str, Any]()
        attributes["subject"] = None
        attributes["timestamp"] = None
        attributes["recipients"] = None
        attributes["text"] = None
        if unread_thread is not None:
            attributes["subject"] = unread_thread["subject"]
            attributes["recipients"] = ", ".join(rec["answer_directly_name"] for rec in unread_thread["recipients"])
            if unread_thread["extra_recipients_count"] > 0:
                attributes["recipients"] += f", +{unread_thread["extra_recipients_count"]}"
            latestmsg = None if "latest_message" not in unread_thread else unread_thread["latest_message"]
            if latestmsg is not None:
                attributes["timestamp"] = None if "send_datetime" not in latestmsg else latestmsg["send_datetime"]
                text = None if "text" not in latestmsg else latestmsg["text"]
                html = None if text is None else text["html"]
                attributes["text"] = html
        self._attr_extra_state_attributes = attributes