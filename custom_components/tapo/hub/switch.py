from typing import cast
from typing import Optional

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from custom_components.tapo.hub.tapo_hub_child_coordinator import (
    TapoHubChildCoordinator,
)
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.ke100_device import KE100Device


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        switch_factories = SWITCH_MAPPING.get(type(child_coordinator.device), [])
        async_add_entities(
            [factory(child_coordinator) for factory in switch_factories], True
        )


class SwitchTapoChild(BaseTapoHubChildEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: TapoHubChildCoordinator):
        super().__init__(coordinator)

    @property
    def is_on(self) -> Optional[bool]:
        return (
            cast(TapoHubChildCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .device_on
        )

    async def async_turn_on(self, **kwargs):
        (
            await cast(TapoHubChildCoordinator, self.coordinator).device.on()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (
            await cast(TapoHubChildCoordinator, self.coordinator).device.off()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()


# Perhaps unneeded as Climate Entity provides this functionality
# These can be extracted into common functionality
class TRVFrostProtection(BaseTapoHubChildEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Frost Protection"

    def __init__(self, coordinator: TapoHubChildCoordinator):
        super().__init__(coordinator)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def is_on(self) -> Optional[bool]:
        return (
            cast(TapoHubChildCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .frost_protection_on
        )

    @property
    def device_class(self) -> Optional[str]:
        return SwitchDeviceClass.SWITCH

    async def async_turn_on(self, **kwargs):
        (
            await cast(
                TapoHubChildCoordinator, self.coordinator
            ).device.set_frost_protection_on()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (
            await cast(
                TapoHubChildCoordinator, self.coordinator
            ).device.set_frost_protection_off()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()


class TRVChildLock(BaseTapoHubChildEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Child Lock"

    def __init__(self, coordinator: TapoHubChildCoordinator):
        super().__init__(coordinator)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SwitchDeviceClass.SWITCH

    @property
    def is_on(self) -> Optional[bool]:
        return (
            cast(TapoHubChildCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .child_protection
        )

    async def async_turn_on(self, **kwargs):
        (
            await cast(
                TapoHubChildCoordinator, self.coordinator
            ).device.set_child_protection_on()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (
            await cast(
                TapoHubChildCoordinator, self.coordinator
            ).device.set_child_protection_off()
        ).get_or_raise()
        await self.coordinator.async_request_refresh()


SWITCH_MAPPING = {
    SwitchChildDevice: [SwitchTapoChild],
    KE100Device: [TRVFrostProtection, TRVChildLock],
}
