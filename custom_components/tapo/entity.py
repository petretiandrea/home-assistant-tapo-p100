import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry, device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.devices.base import TapoDevice
from plugp100.devices.children.strip_socket import TapoStripSocket

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoDataCoordinator

_LOGGER = logging.getLogger(__name__)


def tapo_device_info(device: TapoDevice) -> DeviceInfo:
    """Device info of a tapo device, identified by its id and MAC address."""
    return {
        "identifiers": {(DOMAIN, device.device_id)},
        "name": device.nickname,
        "model": device.model,
        "manufacturer": "TP-Link",
        "sw_version": device.firmware_version,
        "hw_version": device.device_info.hardware_version,
        "connections": {
            (device_registry.CONNECTION_NETWORK_MAC, dr.format_mac(device.mac))
        },
    }


def strip_socket_device_info(
    hass: HomeAssistant | None, socket: TapoStripSocket, config_entry_id: str
) -> DeviceInfo:
    """Device info of a power strip socket, linked to the strip's device.

    Strip sockets all share the strip's MAC, so including the MAC connection in
    device_info causes HA to merge all socket devices into the strip device. Use
    only the unique per-socket identifier and link the socket to the strip.
    """
    info: DeviceInfo = {
        "identifiers": {(DOMAIN, socket.device_id)},
        "name": socket.nickname,
        "model": socket.model,
        "manufacturer": "TP-Link",
        "sw_version": socket.firmware_version,
        "hw_version": socket.device_info.hardware_version,
    }
    parent_id = socket._parent_info.device_id
    if "via_device_id" not in dr.DeviceInfo.__optional_keys__:
        # Home Assistant before `via_device_id` was added to DeviceInfo.
        info["via_device"] = (DOMAIN, parent_id)  # type: ignore[typeddict-unknown-key]
    elif hass is not None and (
        parent := dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, parent_id), config_entry_id
        )
    ):
        info["via_device_id"] = parent.id
    return info


class CoordinatedTapoEntity(CoordinatorEntity[TapoDataCoordinator]):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
        super().__init__(coordinator)
        self.device: TapoDevice = device
        self._device_info = tapo_device_info(device)

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def unique_id(self):
        return self.device.device_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
