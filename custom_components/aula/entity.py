from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Generic, TypeVar
import logging

from .const import DOMAIN, MANUFACTRURER
from .aula_data_coordinator import AulaDataCoordinator, AulaDataCoordinatorData
from .aula_calendar_coordinator import AulaCalendarCoordinator, AulaCalendarCoordinatorData

_LOGGER = logging.getLogger(__name__)
CONTEXT_TYPE = TypeVar("CONTEXT_TYPE")

class AulaEntityBase(Generic[CONTEXT_TYPE], CoordinatorEntity[AulaDataCoordinator]):
    _attr_has_entity_name = True
    _data: AulaDataCoordinatorData

    def __init__(self, coordinator: AulaDataCoordinator, name: str, context: CONTEXT_TYPE) -> None:
        super().__init__(coordinator, context)
        self._attr_translation_key = name
        self._attr_unique_id = self._attr_translation_key
        #set initial values

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_values(self.coordinator.data, self.coordinator_context)
        self.async_write_ha_state()

    def _init_data(self) -> None:
        self._set_values(self.coordinator.data, self.coordinator_context)

    def _set_values(self, data: AulaDataCoordinatorData, context: CONTEXT_TYPE):
        self._data = data
        pass

    @property
    def device_info(self): # type: ignore
        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_id,
            "manufacturer": MANUFACTRURER,
            "sw_version": f"{self.coordinator.aula_version}",
        }
        return info


class AulaCalendarEntityBase(CoordinatorEntity[AulaCalendarCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AulaCalendarCoordinator, name: str) -> None:
        super().__init__(coordinator, context=None)
        self._attr_translation_key = name
        self._attr_unique_id = self._attr_translation_key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._handle_data_updated(self.coordinator.data):
            self.async_write_ha_state()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        """Handle the update and return True if data has changed for the entity."""
        return False

    @property
    def device_info(self): # type: ignore
        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_id,
            "manufacturer": MANUFACTRURER,
            "sw_version": f"{self.coordinator.aula_version}",
        }
        return info