from typing import cast
from typing import Optional

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.water_leak_device import WaterLeakSensor as WaterLeakDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensor_factories = SENSOR_MAPPING.get(type(child_coordinator.device), [])
        async_add_entities(
            [factory(child_coordinator) for factory in sensor_factories], True
        )


class SmartDoorSensor(BaseTapoHubChildEntity, BinarySensorEntity):
    def __init__(self, coordinator: TapoDataCoordinator):
        super().__init__(coordinator)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.DOOR

    @property
    def is_on(self) -> bool:
        return (
            cast(TapoDataCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .is_open
        )


class WaterLeakSensor(BaseTapoHubChildEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoDataCoordinator):
        super().__init__(coordinator)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self) -> bool:
        return (
            cast(TapoDataCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .water_leak_status
            != "normal"
        )


class MotionSensor(BaseTapoHubChildEntity, BinarySensorEntity):
    def __init__(self, coordinator: TapoDataCoordinator):
        super().__init__(coordinator)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool:
        return (
            cast(TapoDataCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .detected
        )


class LowBatterySensor(BaseTapoHubChildEntity, BinarySensorEntity):
    def __init__(self, coordinator: TapoDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Battery Low"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.BATTERY

    @property
    def is_on(self) -> bool:
        return (
            cast(TapoDataCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .base_info.at_low_battery
        )


SENSOR_MAPPING = {
    T31Device: [LowBatterySensor],
    T110SmartDoor: [SmartDoorSensor, LowBatterySensor],
    S200ButtonDevice: [LowBatterySensor],
    T100MotionSensor: [MotionSensor, LowBatterySensor],
    SwitchChildDevice: [LowBatterySensor],
    WaterLeakDevice: [WaterLeakSensor, LowBatterySensor],
    KE100Device: [LowBatterySensor],
}
