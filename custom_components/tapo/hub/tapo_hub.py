import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import List

from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import HUB_PLATFORMS
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.tapo_hub_child_coordinator import (
    TapoHubChildCoordinator,
)
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.hub.hub_device_tracker import DeviceAdded
from plugp100.api.hub.hub_device_tracker import HubDeviceEvent
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.responses.device_state import DeviceInfo
from plugp100.responses.hub_childs.hub_child_base_info import HubChildBaseInfo

_LOGGER = logging.getLogger(__name__)


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

        device_list = (
            (await self.hub.get_children()).get_or_else([]).get_children_base_info()
        )
        _LOGGER.info(
            "Found %d children associated to hub %s",
            len(device_list),
            device_info.device_id,
        )
        child_coordinators = await self.setup_children(
            hass, registry, device_list, polling_rate
        )
        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=hub_coordinator,
            config_entry_update_unsub=self.entry.add_update_listener(
                _on_options_update_listener
            ),
            child_coordinators=child_coordinators,
        )

        # TODO: refactory with add_device and remove_device methods
        initial_device_ids = list(map(lambda x: x.device_id, device_list))

        async def _handle_child_device_event(event: HubDeviceEvent):
            _LOGGER.info("Detected child association change %s", str(event))
            if event.device_id not in initial_device_ids:
                await hass.config_entries.async_reload(self.entry.entry_id)
            elif event is DeviceAdded:
                initial_device_ids.remove(event.device_id)

        self.entry.async_on_unload(
            self.hub.subscribe_device_association(_handle_child_device_event)
        )

        await hass.config_entries.async_forward_entry_setups(self.entry, HUB_PLATFORMS)
        return True

    async def setup_children(
        self,
        hass: HomeAssistant,
        registry: DeviceRegistry,
        device_list: list[HubChildBaseInfo],
        polling_rate: timedelta,
    ) -> List[TapoHubChildCoordinator]:
        setup_results = [
            await self._add_hass_tapo_child_device(
                hass, registry, child_device, polling_rate
            )
            for child_device in device_list
        ]
        device_entries, child_coordinators = zip(*setup_results)

        # delete device which is no longer available to hub
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            # avoid delete hub device which has a connection
            if (
                device.id not in map(lambda x: x.id, device_entries)
                and len(device.connections) == 0
            ):
                registry.async_remove_device(device.id)

        return child_coordinators

    async def _add_hass_tapo_child_device(
        self,
        hass: HomeAssistant,
        registry: DeviceRegistry,
        device_state: HubChildBaseInfo,
        polling_rate: timedelta,
    ) -> (DeviceEntry, TapoHubChildCoordinator):
        entry = self._hass_add_child_device(registry, device_state)
        child_device = _create_child_device(device_state, self.hub)
        coordinator = TapoHubChildCoordinator(hass, child_device, polling_rate)
        await coordinator.async_config_entry_first_refresh()
        return (entry, coordinator)

    def _hass_add_child_device(
        self, registry: DeviceRegistry, device_state: HubChildBaseInfo
    ) -> DeviceEntry:
        return registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, device_state.device_id)},
            model=device_state.model,
            name=device_state.nickname,
            manufacturer="TP-Link",
            sw_version=device_state.firmware_version,
            hw_version=device_state.hardware_version,
        )


def _create_child_device(child_state: HubChildBaseInfo, hub: HubDevice):
    model = child_state.model.lower()
    device_id = child_state.device_id
    if "t31" in model:
        return T31Device(hub, device_id)
    elif "t110" in model:
        return T110SmartDoor(hub, device_id)
    elif "s200" in model:
        return S200ButtonDevice(hub, device_id)
    elif "t100" in model:
        return T100MotionSensor(hub, device_id)
    elif "ke100" in model:
        return KE100Device(hub, device_id)
    elif any(supported in model for supported in ["s220", "s210"]):
        return SwitchChildDevice(hub, device_id)
    return None


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
