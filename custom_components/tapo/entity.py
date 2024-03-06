import logging
from typing import TypeVar

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoDataCoordinator
from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.responses.device_state import DeviceInfo as TapoDeviceInfo

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
C = TypeVar("C", bound=TapoDataCoordinator)


class CoordinatedTapoEntity(CoordinatorEntity[C]):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: C):
        super().__init__(coordinator)
        self._base_data = self.coordinator.get_state_of(TapoDeviceInfo)

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._base_data.device_id)},
            "name": self._base_data.friendly_name,
            "model": self._base_data.model,
            "manufacturer": "TP-Link",
            "sw_version": self._base_data.firmware_version,
            "hw_version": self._base_data.hardware_version,
            "connections": {
                (device_registry.CONNECTION_NETWORK_MAC, self._base_data.mac)
            },
        }

    @property
    def unique_id(self):
        return self._base_data.device_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self._base_data = self.coordinator.get_state_of(TapoDeviceInfo)
        self.async_write_ha_state()
