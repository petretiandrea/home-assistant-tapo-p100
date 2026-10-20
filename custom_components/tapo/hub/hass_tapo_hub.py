from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import List

from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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
from custom_components.tapo.hub.local_push import (
    CONF_LOCAL_PUSH_DEVICES,
    CONF_LOCAL_PUSH_HOST,
    CONF_LOCAL_PUSH_PORT,
    DEFAULT_LOCAL_PUSH_PORT,
    LocalPushManager,
)

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
        try:
            await self._async_setup_local_push(hass, child_coordinators)
        except BaseException:
            hass.data[DOMAIN][self.entry.entry_id].config_entry_update_unsub()
            raise
        # TODO: refactory with add_device and remove_device methods
        initial_device_ids = list(map(lambda x: x.device_id, self.hub.children))

        async def _handle_child_device_event(event: HubDeviceEvent):
            _LOGGER.info("Detected child association change %s", str(event))
            if event.device_id not in initial_device_ids:
                await hass.config_entries.async_reload(self.entry.entry_id)
            elif isinstance(event, DeviceAdded):
                initial_device_ids.remove(event.device_id)

        self.entry.async_on_unload(
            self.hub.subscribe_device_association(_handle_child_device_event)
        )

        try:
            await hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)
        except BaseException:
            data = hass.data[DOMAIN][self.entry.entry_id]
            if data.local_push:
                await data.local_push.async_stop()
            data.config_entry_update_unsub()
            raise
        return True

    async def _async_setup_local_push(self, hass, child_coordinators):
        """Replace the event transport for H100/S200D, preserving other devices."""
        available = {
            child.device_id for child in self.hub.children if child.model == "S200D"
        }
        if self.hub.model != "H100":
            available = set()
        selected = set(self.entry.data.get(CONF_LOCAL_PUSH_DEVICES, sorted(available)))
        for coordinator in child_coordinators:
            coordinator._local_push_managed = coordinator.device.device_id in available
        if selected:
            if not selected <= available:
                raise ValueError(
                    "A selected local push knob is not associated with this hub"
                )
            host = self.entry.data.get(
                CONF_LOCAL_PUSH_HOST
            ) or await async_get_source_ip(hass, target_ip=self.entry.data["host"])
            push = LocalPushManager(
                hass,
                self.entry,
                self.hub,
                selected,
                host,
                self.entry.data.get(CONF_LOCAL_PUSH_PORT, DEFAULT_LOCAL_PUSH_PORT),
            )
            try:
                await push.async_start()
            except OSError as error:
                await push.async_stop()
                raise ConfigEntryNotReady(
                    f"Local push cannot listen on {host}:{push.port} or UDP 20002. "
                    "Configure the H100 receiver address/port in the integration options."
                ) from error
            except BaseException:
                await push.async_stop()
                raise
            hass.data[DOMAIN][self.entry.entry_id].local_push = push
            for coordinator in child_coordinators:
                if coordinator.device.device_id in selected:
                    coordinator._local_push = push

    async def setup_children(
        self,
        hass: HomeAssistant,
        registry: DeviceRegistry,
        devices: List[TapoDevice],
        polling_rate: timedelta,
    ) -> List[TapoDataCoordinator]:
        coordinators = [
            TapoDataCoordinator(
                hass,
                child_device,
                timedelta(milliseconds=DEFAULT_BUTTON_POLLING_RATE_MS)
                if isinstance(child_device, TriggerButtonDevice)
                and not (self.hub.model == "H100" and child_device.model == "S200D")
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
