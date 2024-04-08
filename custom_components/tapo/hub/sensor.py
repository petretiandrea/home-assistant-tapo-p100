from datetime import date
from datetime import datetime
from typing import Optional
from typing import Union
from typing import cast

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
from plugp100.new.components.battery_component import BatteryComponent
from plugp100.new.components.humidity_component import HumidityComponent
from plugp100.new.components.report_mode_component import ReportModeComponent
from plugp100.new.components.temperature_component import TemperatureComponent
from plugp100.new.tapodevice import TapoDevice
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity

COMPONENT_MAPPING = {
    HumidityComponent: 'HumiditySensor',
    TemperatureComponent: 'TemperatureSensor',
    ReportModeComponent: 'ReportIntervalDiagnostic',
    BatteryComponent: 'BatteryLevelSensor'
}


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensors = [
            eval(cls)(child_coordinator, child_coordinator.device)
            for (component, cls) in COMPONENT_MAPPING.items()
            if child_coordinator.device.has_component(component)
        ]
        # temporary workaround to avoid getting battery percentage on not supported devices
        if battery := child_coordinator.device.get_component(BatteryComponent):
            if battery.battery_percentage == -1:
                sensors = list(filter(lambda x: not isinstance(x, BatteryLevelSensor), sensors))

        async_add_entities(sensors, True)


class HumiditySensor(CoordinatedTapoEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
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
        if humidity := self.device.get_component(HumidityComponent):
            return humidity.current_humidity
        return None


class TemperatureSensor(CoordinatedTapoEntity, SensorEntity):
    _attr_has_entity_name = True

    _temperature_component: TemperatureComponent

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
        self._attr_name = "Temperature"
        self._temperature_component = device.get_component(TemperatureComponent)

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
        if self._temperature_component.temperature_unit == TemperatureUnit.CELSIUS:
            return UnitOfTemperature.CELSIUS
        elif self._temperature_component.temperature_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        else:
            return None

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return self._temperature_component.current_temperature


class BatteryLevelSensor(CoordinatedTapoEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
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
        return self.device.get_component(BatteryComponent).battery_percentage


class ReportIntervalDiagnostic(CoordinatedTapoEntity, SensorEntity):

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
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
        return self.device.get_component(ReportModeComponent).report_interval_seconds
