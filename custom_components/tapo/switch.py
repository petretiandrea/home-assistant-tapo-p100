from typing import cast
from typing import Optional

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import PowerStripChildrenState
from custom_components.tapo.coordinators import TapoDeviceCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.hub.switch import (
    async_setup_entry as async_setup_hub_switch,
)
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.api.plug_device import PlugDevice
from plugp100.api.power_strip_device import PowerStripDevice
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.responses.device_state import PlugDeviceState


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if data.coordinator.is_hub:
        await async_setup_hub_switch(hass, entry, async_add_entities)
    else:
        await async_setup_device_switch(hass, entry, async_add_entities)


async def async_setup_device_switch(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if isinstance(data.coordinator.device, PlugDevice):
        async_add_devices([TapoPlugEntity(data.coordinator)], True)
    elif isinstance(data.coordinator.device, PowerStripDevice):
        children = list(data.coordinator.get_state_of(PowerStripChildrenState).values())
        async_add_devices(
            [StripPlugEntity(data.coordinator, child.device_id) for child in children],
            True,
        )


class TapoPlugEntity(CoordinatedTapoEntity[TapoDeviceCoordinator], SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: TapoDeviceCoordinator):
        super().__init__(coordinator)

    @property
    def is_on(self) -> Optional[bool]:
        return self.coordinator.get_state_of(PlugDeviceState).device_on

    async def async_turn_on(self, **kwargs):
        (await self.coordinator.device.on()).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.coordinator.device.off()).get_or_raise()
        await self.coordinator.async_request_refresh()


class StripPlugEntity(CoordinatorEntity[TapoDeviceCoordinator], SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoDeviceCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_name = f"{self._get_child_state().nickname}"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_info.device_id)},
            "name": self.coordinator.device_info.model,
            "model": self.coordinator.device_info.model,
            "manufacturer": "TP-Link",
            "sw_version": self.coordinator.device_info.firmware_version,
            "hw_version": self.coordinator.device_info.hardware_version,
        }

    @property
    def unique_id(self):
        return self.device_id

    @property
    def is_on(self) -> Optional[bool]:
        return self._get_child_state().device_on

    async def async_turn_on(self, **kwargs):
        (await self.coordinator.device.on(self.device_id)).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.coordinator.device.off(self.device_id)).get_or_raise()
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    def _get_child_state(self) -> PowerStripChild:
        return self.coordinator.get_state_of(PowerStripChildrenState).get(
            self.device_id
        )
