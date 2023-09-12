import base64
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import HUB_PLATFORMS
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.api.hub.hub_device import HubDevice
from plugp100.responses.device_state import DeviceInfo


@dataclass
class TapoHub:
    entry: ConfigEntry
    hub: HubDevice

    async def initialize_hub(self, hass: HomeAssistant):
        polling_rate = timedelta(
            seconds=self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        hub_coordinator = TapoHubCoordinator(hass, self.hub, polling_rate)
        await hub_coordinator.async_config_entry_first_refresh()
        device_info = hub_coordinator.get_state_of(DeviceInfo)
        registry: DeviceRegistry = device_registry.async_get(hass)
        registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            connections={(device_registry.CONNECTION_NETWORK_MAC, device_info.mac)},
            identifiers={(DOMAIN, device_info.device_id)},
            name=device_info.friendly_name,
            model=device_info.model,
            manufacturer="TP-Link",
            sw_version=device_info.firmware_version,
            hw_version=device_info.hardware_version,
        )

        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=hub_coordinator,
            config_entry_update_unsub=self.entry.add_update_listener(
                _on_options_update_listener
            ),
        )
        await hass.config_entries.async_forward_entry_setups(self.entry, HUB_PLATFORMS)
        # TODO: here we will add others children devices as device different
        # and then send to platform setups. Inspired by hue integration
        # TIPS: attach to hub coordinator to handle device removal
        await self.setup_child_devices(registry)

        return True

    async def setup_child_devices(self, registry: DeviceRegistry):
        device_list = (
            (await self.hub.get_children()).get_or_else([]).get_children(lambda x: x)
        )
        knwon_children = [
            self.add_child_device(registry, device_state)
            for device_state in device_list
        ]

        # delete device which is no longer available to hub
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            # avoid delete hub device which has a connection
            if device not in knwon_children and device.connections is []:
                registry.async_remove_device(device.id)

    def add_child_device(
        self, registry: DeviceRegistry, device_state: dict[str, Any]
    ) -> DeviceEntry:
        return registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, device_state["device_id"])},
            model=device_state["model"],
            name=base64.b64decode(device_state["nickname"]).decode("UTF-8"),
            manufacturer="TP-Link",
            sw_version=device_state["fw_ver"],
            hw_version=device_state["hw_ver"],
        )


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
