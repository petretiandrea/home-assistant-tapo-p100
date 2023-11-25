from datetime import date
from datetime import datetime
from typing import cast
from typing import Optional
from typing import Union

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.const import PERCENTAGE
from homeassistant.const import UnitOfTemperature
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.water_leak_device import WaterLeakSensor as WaterLeakDevice
from plugp100.responses.temperature_unit import TemperatureUnit


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensor_factories = SENSOR_MAPPING.get(type(child_coordinator.device), [])
        async_add_entities(
            [factory(child_coordinator) for factory in sensor_factories], True
        )


class HumitidySensor(BaseTapoHubChildEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Humidity"

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self) -> Optional[str]:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return PERCENTAGE

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .current_humidity
        )


class TemperatureSensor(BaseTapoHubChildEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Temperature"

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self) -> Optional[str]:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        temp_unit = (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .temperature_unit
        )
        if temp_unit == TemperatureUnit.CELSIUS:
            return UnitOfTemperature.CELSIUS
        elif temp_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        else:
            return None

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .current_temperature
        )


class BatteryLevelSensor(BaseTapoHubChildEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Battery Percentage"

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> Optional[str]:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return PERCENTAGE

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .battery_percentage
        )


class ReportIntervalDiagnostic(BaseTapoHubChildEntity, SensorEntity):
    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Report Interval"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> Optional[str]:
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return UnitOfTime.SECONDS

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .report_interval_seconds
        )


SENSOR_MAPPING = {
    T31Device: [HumitidySensor, TemperatureSensor, ReportIntervalDiagnostic],
    T110SmartDoor: [ReportIntervalDiagnostic],
    S200ButtonDevice: [ReportIntervalDiagnostic],
    T100MotionSensor: [ReportIntervalDiagnostic],
    WaterLeakDevice: [ReportIntervalDiagnostic],
    KE100Device: [TemperatureSensor, BatteryLevelSensor],
}
