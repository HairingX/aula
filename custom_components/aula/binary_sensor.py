from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Any, List
import logging

from .entity import AulaEntityBase
from .aula_data_coordinator import AulaDataCoordinator, AulaDataCoordinatorData
from .aula_data import get_aula_data_coordinator
from .aula_proxy.module import AulaMessageThread, AulaAlbumNotification, AulaCalendarEventNotification, AulaGalleryNotification, AulaPostNotification

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup binary sensors from a config entry created in the integrations UI."""
    coordinator = get_aula_data_coordinator(hass, entry)
    entities: List[BinarySensorEntity] = []
    entities.append(AulaUnreadMessageBinarySensor(coordinator))
    entities.append(AulaUnreadGalleryBinarySensor(coordinator))
    entities.append(AulaUnreadCalendarEventBinarySensor(coordinator))
    entities.append(AulaUnreadPostBinarySensor(coordinator))
    async_add_entities(entities)


class AulaUnreadGalleryBinarySensor(AulaEntityBase[None], BinarySensorEntity): # type: ignore
    def __init__(self, coordinator: AulaDataCoordinator):
        super().__init__(coordinator, name="unread_gallery", context=None)
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context:None) -> None:
        self._attr_is_on = False
        notifications = data.notifications
        total = 0
        for notification in notifications:
            if  isinstance(notification, AulaGalleryNotification):
                total += len(notification.media_ids)
            elif isinstance(notification, AulaAlbumNotification):
                total += 1

        self._attr_is_on = total > 0
        self._attr_icon = 'mdi:image-album'
        attributes = dict[str, Any]()
        attributes["total"] = total
        self._attr_extra_state_attributes = attributes

class AulaUnreadCalendarEventBinarySensor(AulaEntityBase[None], BinarySensorEntity): # type: ignore
    def __init__(self, coordinator: AulaDataCoordinator):
        super().__init__(coordinator, name="unread_calendar", context=None)
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context:None) -> None:
        self._attr_is_on = False
        notifications = data.notifications
        total = 0
        first: AulaCalendarEventNotification|None = None
        for notification in notifications:
            if  isinstance(notification, AulaCalendarEventNotification):
                total += 1
                if not first: first = notification

        self._attr_is_on = total > 0
        self._attr_icon = 'mdi:calendar-badge'
        attributes = dict[str, Any]()
        attributes["total"] = total
        attributes["all_day"] = None
        attributes["end_datetime"] = None
        attributes["start_datetime"] = None
        attributes["title"] = None
        if first:
            attributes["all_day"] = first.is_all_day_event
            attributes["end_datetime"] = first.end_datetime
            attributes["start_datetime"] = first.start_datetime
            attributes["title"] = first.title
        self._attr_extra_state_attributes = attributes

class AulaUnreadMessageBinarySensor(AulaEntityBase[None], BinarySensorEntity): # type: ignore
    def __init__(self, coordinator: AulaDataCoordinator):
        super().__init__(coordinator, name="unread_message", context=None)
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context:None) -> None:
        self._attr_is_on = False
        threads = data.message_threads
        first: AulaMessageThread|None = None
        total = 0
        for thread in threads:
            if not thread.read:
                total += 1
                if not first: first = thread

        self._attr_is_on = first is not None
        self._attr_icon = 'mdi:message-badge'
        attributes = dict[str, Any]()
        attributes["total"] = total
        attributes["subject"] = None
        attributes["timestamp"] = None
        attributes["recipients"] = None
        attributes["text"] = None
        if first is not None:
            attributes["subject"] = first.subject
            attributes["recipients"] = ", ".join(rec.answer_directly_name for rec in first.recipients)
            if first.extra_recipients_count > 0:
                attributes["recipients"] += f", +{first.extra_recipients_count}"
            latestmsg = first.latest_message
            if latestmsg is not None:
                attributes["timestamp"] = latestmsg.send_datetime
                text = latestmsg.text
                html = None if text is None else text.html
                attributes["text"] = html
        self._attr_extra_state_attributes = attributes

class AulaUnreadPostBinarySensor(AulaEntityBase[None], BinarySensorEntity): # type: ignore
    def __init__(self, coordinator: AulaDataCoordinator):
        super().__init__(coordinator, name="unread_post", context=None)
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context:None) -> None:
        self._attr_is_on = False
        notifications = data.notifications
        total = 0
        first: AulaPostNotification|None = None
        for notification in notifications:
            if  isinstance(notification, AulaPostNotification):
                total += 1
                if not first: first = notification

        self._attr_is_on = total > 0
        self._attr_icon = 'mdi:bulletin-board'
        attributes = dict[str, Any]()
        attributes["total"] = total
        attributes["title"] = None
        if first:
            attributes["title"] = first.title
        self._attr_extra_state_attributes = attributes