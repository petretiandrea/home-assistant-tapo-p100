from typing import Optional
from typing import cast

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.new.child.tapohubchildren import SwitchChildDevice, KE100Device

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        device = child_coordinator.device
        if isinstance(device, SwitchChildDevice):
            async_add_entities([
                SwitchTapoChild(child_coordinator, device)
            ], True)
        elif isinstance(device, KE100Device):
            async_add_entities([
                TRVFrostProtection(child_coordinator, device),
                TRVChildLock(child_coordinator, device)
            ], True)


class SwitchTapoChild(CoordinatedTapoEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    device: SwitchChildDevice

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: SwitchChildDevice
    ) -> None:
        super().__init__(coordinator, device)

    @property
    def is_on(self) -> Optional[bool]:
        return self.device.is_on

    async def async_turn_on(self, **kwargs):
        (await self.device.on()).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.device.off()).get_or_raise()
        await self.coordinator.async_request_refresh()


# Perhaps unneeded as Climate Entity provides this functionality
# These can be extracted into common functionality
class TRVFrostProtection(CoordinatedTapoEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Frost Protection"

    device: KE100Device

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: KE100Device
    ) -> None:
        super().__init__(coordinator, device)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def is_on(self) -> Optional[bool]:
        return self.device.is_frost_protection_on == 1

    @property
    def device_class(self) -> Optional[str]:
        return SwitchDeviceClass.SWITCH

    async def async_turn_on(self, **kwargs):
        (await self.device.set_frost_protection_on()).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.device.set_frost_protection_off()).get_or_raise()
        await self.coordinator.async_request_refresh()


class TRVChildLock(CoordinatedTapoEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Child Lock"

    device: KE100Device

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: KE100Device
    ) -> None:
        super().__init__(coordinator, device)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SwitchDeviceClass.SWITCH

    @property
    def is_on(self) -> Optional[bool]:
        return self.device.is_child_protection_on == 1

    async def async_turn_on(self, **kwargs):
        (await self.device.set_child_protection_on()).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.device.set_child_protection_off()).get_or_raise()
        await self.coordinator.async_request_refresh()
