import asyncio

from datetime import date
from datetime import datetime
from enum import StrEnum
from typing import Optional
from typing import Union
from typing import cast

from homeassistant.components.event import EventEntity, EventDeviceClass
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
from plugp100.new.components.trigger_log_component import TriggerLogComponent
from plugp100.new.tapodevice import TapoDevice
from plugp100.responses.hub_childs.s200b_device_state import (
    SingleClickEvent,
    DoubleClickEvent,
    RotationEvent,
)
from plugp100.responses.hub_childs.trigger_log_response import TriggerLogResponse
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity

COMPONENT_MAPPING = {
    HumidityComponent: 'HumiditySensor',
    TemperatureComponent: 'TemperatureSensor',
    ReportModeComponent: 'ReportIntervalDiagnostic',
    BatteryComponent: 'BatteryLevelSensor',
    TriggerLogComponent: 'TriggerEvent'
}

class TriggerEventTypes(StrEnum):
    """Available event types reported by the TriggerEvent entity."""

    SINGLE_PRESS = "single_press"
    DOUBLE_PRESS = "double_press"
    ROTATE_CLOCKWISE = "rotate_clockwise"
    ROTATE_ANTICLOCKWISE = "rotate_anticlockwise"

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

class TriggerEvent(CoordinatedTapoEntity, EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [TriggerEventTypes.SINGLE_PRESS, TriggerEventTypes.DOUBLE_PRESS, TriggerEventTypes.ROTATE_CLOCKWISE, TriggerEventTypes.ROTATE_ANTICLOCKWISE]
    _attr_has_entity_name = True
    _task: Optional[asyncio.tasks.Task] = None
    _last_event_id: Optional[int] = None

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
        self._attr_name = "Trigger Event"

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    async def event_loop(self):
        while True:
            # Just request 1 event at a time. This is simple and may result in lost events however.
            # TODO: A better approach may be to cache the last n IDs and try to submit all missing events in order.
            maybe_response = await self.device.get_component(TriggerLogComponent).get_event_logs(1)
            response = maybe_response.get_or_else(TriggerLogResponse(0, 0, []))

            if self._last_event_id is None and len(response.events) > 0:
                # Skip the first event on startup to avoid re-reporting of historical events.
                self._last_event_id = response.events[0].id
            elif not self._last_event_id is None and self._last_event_id != response.events[0].id:
                if isinstance(response.events[0], SingleClickEvent):
                    self._trigger_event(TriggerEventTypes.SINGLE_PRESS)
                elif isinstance(response.events[0], DoubleClickEvent):
                    self._trigger_event(TriggerEventTypes.DOUBLE_PRESS)
                elif isinstance(response.events[0], RotationEvent) and response.events[0].degrees >= 0:
                    self._trigger_event(TriggerEventTypes.ROTATE_CLOCKWISE)
                elif isinstance(response.events[0], RotationEvent) and response.events[0].degrees < 0:
                    self._trigger_event(TriggerEventTypes.ROTATE_ANTICLOCKWISE)

                self.async_write_ha_state()
                self._last_event_id = response.events[0].id

            await asyncio.sleep(1)

    async def async_added_to_hass(self) -> None:
        self._task = asyncio.create_task(self.event_loop())

    async def async_will_remove_from_hass(self) -> None:
        self._task.cancel()