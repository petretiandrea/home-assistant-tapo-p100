from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from . import HassTapoDeviceData
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
        hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    oui = format_mac(data.coordinator.device.mac)[:8].upper()
    children_diagnostics = []
    if len(data.child_coordinators) > 0:
        children_diagnostics = [
            { 'nickname': child.device.nickname, 'raw_state': child.device.raw_state }
            for child in data.child_coordinators
        ]
    return {
        'oui': oui,
        'protocol_name': data.coordinator.device.protocol_version,
        'raw_state': data.coordinator.device.raw_state,
        'components': data.coordinator.device.components,
        'children': children_diagnostics
    }
