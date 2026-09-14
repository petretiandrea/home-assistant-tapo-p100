from typing import Optional, cast

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.devices.children.strip_socket import TapoStripSocket
from plugp100.devices.plug import TapoPlug

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import (
    CoordinatedTapoEntity,
    strip_socket_device_info,
)
from custom_components.tapo.hub.switch import (
    async_setup_entry as async_setup_hub_switch,
)


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
    device = data.coordinator.device
    if isinstance(device, TapoPlug):
        if device.is_strip:
            async_add_devices(
                [TapoPlugEntity(data.coordinator, sock) for sock in device.sockets],
                True,
            )
        else:
            async_add_devices([TapoPlugEntity(data.coordinator, device)], True)


class TapoPlugEntity(CoordinatedTapoEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        plug: TapoPlug | TapoStripSocket,
    ):
        super().__init__(coordinator, plug)
        self._plug = plug
        self._attr_name = f"{self.device.nickname}"

    @property
    def device_info(self):
        if isinstance(self._plug, TapoStripSocket):
            return strip_socket_device_info(
                self.hass, self._plug, self.coordinator.config_entry.entry_id
            )
        return self._device_info

    @property
    def is_on(self) -> Optional[bool]:
        return self._plug.is_on

    async def async_turn_on(self, **kwargs):
        (await self._plug.turn_on()).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self._plug.turn_off()).get_or_raise()
        await self.coordinator.async_request_refresh()
