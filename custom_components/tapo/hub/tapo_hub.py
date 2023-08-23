from dataclasses import dataclass
from datetime import timedelta

from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import HUB_PLATFORMS
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.api.hub.hub_device import HubDevice
from plugp100.responses.device_state import DeviceInfo


@dataclass
class TapoHub:
    entry: ConfigEntry
    hub: HubDevice

    async def initialize_hub(self, hass: HomeAssistant):
        polling_rate = timedelta(
            seconds=self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        (await self.hub.login()).get_or_raise()
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
        return True


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
