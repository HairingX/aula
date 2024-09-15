from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Generic, TypeVar
import logging

from .const import DOMAIN, MANUFACTRURER
from .aula_coordinator import AulaCoordinator, AulaCoordinatorData

_LOGGER = logging.getLogger(__name__)
CONTEXT_TYPE = TypeVar("CONTEXT_TYPE")

class AulaEntityBase(Generic[CONTEXT_TYPE], CoordinatorEntity[AulaCoordinator]):
    _attr_has_entity_name = True
    _data: AulaCoordinatorData

    def __init__(self, coordinator: AulaCoordinator, name: str, context: CONTEXT_TYPE) -> None:
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

    def _set_values(self, data: AulaCoordinatorData, context: CONTEXT_TYPE):
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