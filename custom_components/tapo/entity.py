import logging
from homeassistant.helpers import device_registry as dr

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.new.tapodevice import TapoDevice

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoDataCoordinator

_LOGGER = logging.getLogger(__name__)


class CoordinatedTapoEntity(CoordinatorEntity[TapoDataCoordinator]):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
        super().__init__(coordinator)
        self.device: TapoDevice = device
        self._device_info = {
            "identifiers": {(DOMAIN, self.device.device_id)},
            "name": self.device.nickname,
            "model": self.device.model,
            "manufacturer": "TP-Link",
            "sw_version": self.device.firmware_version,
            "hw_version": self.device.device_info.hardware_version,
            "connections": {
                (device_registry.CONNECTION_NETWORK_MAC, dr.format_mac(self.device.mac))
            },
        }

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def unique_id(self):
        return self.device.device_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
