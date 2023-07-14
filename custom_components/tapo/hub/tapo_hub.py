from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.api.hub.hub_device import HubDevice

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.helpers import value_or_raise
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator


@dataclass
class TapoHub:
    entry: ConfigEntry
    hub: HubDevice

    async def initialize_hub(self, hass: HomeAssistant):
        value_or_raise(await self.hub.login())
        hub_coordinator = TapoHubCoordinator(hass, self.hub, timedelta(seconds=10))
        await hub_coordinator.async_config_entry_first_refresh()
        hub_data = value_or_raise(await self.hub.get_state())
        registry: DeviceRegistry = device_registry.async_get(hass)
        registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            connections={(device_registry.CONNECTION_NETWORK_MAC, hub_data.info.mac)},
            identifiers={(DOMAIN, hub_data.info.device_id)},
            name=hub_data.info.nickname,
            model=hub_data.info.model,
            manufacturer="TP-Link",
            sw_version=hub_data.info.firmware_version,
            hw_version=hub_data.info.hardware_version,
        )

        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=hub_coordinator, config_entry_update_unsub=None
        )
        await hass.config_entries.async_forward_entry_setups(
            self.entry, [Platform.SWITCH]
        )
        # TODO: here we will add others children devices as device different
        # and then send to platform setups. Inspired by hue integration
        return True
