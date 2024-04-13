import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.new.hub_device_tracker import HubDeviceEvent, DeviceAdded
from plugp100.new.tapodevice import TapoDevice
from plugp100.new.tapohub import TapoHub

from custom_components.tapo.const import DEFAULT_POLLING_RATE_S, PLATFORMS
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoDataCoordinator, HassTapoDeviceData

_LOGGER = logging.getLogger(__name__)


@dataclass
class HassTapoHub:
    entry: ConfigEntry
    hub: TapoHub

    async def initialize_hub(self, hass: HomeAssistant):
        polling_rate = timedelta(
            seconds=self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        hub_coordinator = TapoDataCoordinator(hass, self.hub, polling_rate)
        await hub_coordinator.async_config_entry_first_refresh()
        registry: DeviceRegistry = device_registry.async_get(hass)
        registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            connections={(device_registry.CONNECTION_NETWORK_MAC, dr.format_mac(self.hub.mac))},
            identifiers={(DOMAIN, self.hub.device_id)},
            name=self.hub.nickname,
            model=self.hub.model,
            manufacturer="TP-Link",
            sw_version=self.hub.firmware_version,
            hw_version=self.hub.device_info.hardware_version,
        )
        _LOGGER.info(
            "Found %d children associated to hub %s",
            len(self.hub.children),
            self.hub.device_id,
        )
        child_coordinators = await self.setup_children(
            hass, registry, self.hub.children, polling_rate
        )
        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=hub_coordinator,
            config_entry_update_unsub=self.entry.add_update_listener(
                _on_options_update_listener
            ),
            child_coordinators=child_coordinators,
            device=self.hub
        )
        # TODO: refactory with add_device and remove_device methods
        initial_device_ids = list(map(lambda x: x.device_id, self.hub.children))

        async def _handle_child_device_event(event: HubDeviceEvent):
            _LOGGER.info("Detected child association change %s", str(event))
            if event.device_id not in initial_device_ids:
                await hass.config_entries.async_reload(self.entry.entry_id)
            elif event is DeviceAdded:
                initial_device_ids.remove(event.device_id)

        self.entry.async_on_unload(
            self.hub.subscribe_device_association(_handle_child_device_event)
        )

        await hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)
        return True

    async def setup_children(
            self,
            hass: HomeAssistant,
            registry: DeviceRegistry,
            devices: List[TapoDevice],
            polling_rate: timedelta,
    ) -> List[TapoDataCoordinator]:
        coordinators = [
            TapoDataCoordinator(hass, child_device, polling_rate)
            for child_device in devices
        ]

        for coordinator in coordinators:
            await coordinator.async_config_entry_first_refresh()

        device_entries = [
            registry.async_get_or_create(
                config_entry_id=self.entry.entry_id,
                identifiers={(DOMAIN, child_device.device_id)},
                model=child_device.model,
                name=child_device.nickname,
                manufacturer="TP-Link",
                sw_version=child_device.firmware_version,
                hw_version=child_device.device_info.hardware_version,
            )
            for child_device in devices
        ]

        # delete device which is no longer available to hub
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            # avoid delete hub device which has a connection
            if (
                    device.id not in map(lambda x: x.id, device_entries)
                    and len(device.connections) == 0
            ):
                registry.async_remove_device(device.id)

        return coordinators

async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
