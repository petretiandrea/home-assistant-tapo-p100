from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, device_registry as dr
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.devices.base import TapoDevice
from plugp100.devices.children.trigger_button import TriggerButtonDevice
from plugp100.devices.hub import TapoHub
from plugp100.events.hub_device_tracker import DeviceAdded, HubDeviceEvent

from custom_components.tapo.const import (
    DEFAULT_BUTTON_POLLING_RATE_MS,
    DEFAULT_POLLING_RATE_S,
    DOMAIN,
    PLATFORMS,
)
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator

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
            connections={
                (device_registry.CONNECTION_NETWORK_MAC, dr.format_mac(self.hub.mac))
            },
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
            device=self.hub,
        )
        # TODO: refactory with add_device and remove_device methods
        known_device_ids = {child.device_id for child in self.hub.children}

        async def _handle_child_device_event(event: HubDeviceEvent):
            _LOGGER.info("Detected child association change %s", str(event))

            if isinstance(event, DeviceAdded):
                # H110 exposes internal IR/AV virtual children through the
                # association stream. Their IDs are derived from the hub ID,
                # but plugp100 does not expose them in hub.children.
                if event.device_id.startswith(self.hub.device_id):
                    _LOGGER.debug(
                        "Ignoring internal H110 virtual child %s",
                        event.device_id,
                    )
                    return

                # The association subscription can replay DeviceAdded events for
                # children that already existed when the subscription was created.
                if event.device_id in known_device_ids:
                    _LOGGER.debug(
                        "Ignoring DeviceAdded for already known child %s",
                        event.device_id,
                    )
                    return

                known_device_ids.add(event.device_id)
                await hass.config_entries.async_reload(self.entry.entry_id)
                return

            if event.device_id in known_device_ids:
                known_device_ids.discard(event.device_id)
                await hass.config_entries.async_reload(self.entry.entry_id)

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
        button_polling_rate = timedelta(milliseconds=DEFAULT_BUTTON_POLLING_RATE_MS)
        coordinators = [
            TapoDataCoordinator(
                hass,
                child_device,
                button_polling_rate
                if isinstance(child_device, TriggerButtonDevice)
                else polling_rate,
            )
            for child_device in devices
        ]

        for coordinator in coordinators:
            coordinator._hub_entry_id = self.entry.entry_id
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
