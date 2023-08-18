from typing import Any, Dict, Optional, cast

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.plug_device import PlugDevice

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import (
    HassTapoDeviceData,
    PlugDeviceState,
    PlugTapoCoordinator,
)
from custom_components.tapo.entity import BaseTapoEntity
from custom_components.tapo.helpers import value_or_raise
from custom_components.tapo.hub.switch import (
    async_setup_entry as async_setup_hub_switch,
)
from custom_components.tapo.setup_helpers import setup_from_platform_config


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    coordinator = await setup_from_platform_config(hass, config)
    if isinstance(coordinator, PlugTapoCoordinator):
        async_add_entities([TapoPlugEntity(coordinator)], True)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    if entry.data.get("is_hub", False):
        await async_setup_hub_switch(hass, entry, async_add_entities)
    else:
        await async_setup_device_switch(hass, entry, async_add_entities)


async def async_setup_device_switch(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if isinstance(data.coordinator, PlugTapoCoordinator):
        async_add_devices([TapoPlugEntity(data.coordinator)], True)


class TapoPlugEntity(BaseTapoEntity[PlugTapoCoordinator], SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: PlugTapoCoordinator):
        super().__init__(coordinator)

    @property
    def is_on(self) -> Optional[bool]:
        return self.coordinator.get_state_of(PlugDeviceState).device_on

    async def async_turn_on(self, **kwargs):
        value_or_raise(await self.coordinator.device.on())
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        value_or_raise(await self.coordinator.device.off())
        await self.coordinator.async_request_refresh()


# class TapoSubPlugEntity(BaseTapoEntity[PlugDeviceState], SwitchEntity):
#     _attr_has_entity_name = True
#     _attr_device_class = SwitchDeviceClass.OUTLET

#     def __init__(self, coordinator: PowerStripCoordinator, device_id: str):
#         super().__init__(coordinator)
#         self._device_id = device_id
#         self._attr_name = coordinator.get_child_state(device_id).nickname

#     @property
#     def is_on(self) -> Optional[bool]:
#         return (
#             cast(PowerStripCoordinator, self.coordinator)
#             .get_child_state(self._device_id)
#             .device_on
#         )

#     async def async_turn_on(self, **kwargs):
#         value_or_raise(await self.coordinator.on())
#         await self.coordinator.async_request_refresh()

#     async def async_turn_off(self, **kwargs):
#         value_or_raise(await self.device.off())
#         await self.coordinator.async_request_refresh()
