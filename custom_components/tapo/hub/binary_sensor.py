import datetime
from datetime import date
from typing import cast
from typing import Optional
from typing import Union

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensor_factories = SENSOR_MAPPING[type(child_coordinator.device)]
        async_add_entities(
            [factory(child_coordinator) for factory in sensor_factories], True
        )


class SmartDoorSensor(BaseTapoHubChildEntity, SensorEntity):
    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return "door"

    @property
    def state_class(self) -> Optional[str]:
        return None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return None

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .is_open
        )


class LowBatterySensor(BaseTapoHubChildEntity, SensorEntity):
    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Battery Low"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> Optional[str]:
        return None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return None

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .at_low_battery
        )


SENSOR_MAPPING = {
    T31Device: [LowBatterySensor],
    T110SmartDoor: [SmartDoorSensor, LowBatterySensor],
    S200ButtonDevice: [LowBatterySensor],
}
