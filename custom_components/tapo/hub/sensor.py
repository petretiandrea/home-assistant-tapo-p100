from datetime import date, datetime
import logging
from typing import Optional, Union, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.components.battery import BatteryComponent
from plugp100.components.humidity import HumidityComponent
from plugp100.components.report_mode import ReportModeComponent
from plugp100.components.temperature import TemperatureComponent
from plugp100.components.trigger_log import TriggerLogComponent
from plugp100.devices.base import TapoDevice
from plugp100.devices.children.trigger_button import TriggerButtonDevice
from plugp100.models.temperature import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.hub.event import (
    AdaptivePollingState,
    EventLogPollResult,
    fetch_event_logs,
    get_hub_event_log_poller,
)

_LOGGER = logging.getLogger(__name__)

COMPONENT_MAPPING = {
    HumidityComponent: "HumiditySensor",
    TemperatureComponent: "TemperatureSensor",
    ReportModeComponent: "ReportIntervalDiagnostic",
    BatteryComponent: "BatteryLevelSensor",
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
                sensors = list(
                    filter(lambda x: not isinstance(x, BatteryLevelSensor), sensors)
                )

        if isinstance(
            child_coordinator.device, TriggerButtonDevice
        ) and child_coordinator.device.has_component(TriggerLogComponent):
            sensors.append(
                PollLatencySensor(child_coordinator, child_coordinator.device)
            )

        async_add_entities(sensors, True)


class HumiditySensor(CoordinatedTapoEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
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

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
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

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
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
    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
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


class PollLatencySensor(CoordinatedTapoEntity, SensorEntity):
    """Diagnostic view of the shared adaptive polling state."""

    _attr_has_entity_name = True
    _attr_name = "Poll Latency"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:connection"

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        device: TriggerButtonDevice,
    ):
        super().__init__(coordinator, device)
        self._device: TriggerButtonDevice = device
        self._ha_started: bool = False
        self._event_log_poller = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._event_log_poller = get_hub_event_log_poller(
            self.hass,
            self.coordinator,
            self._device,
            getattr(self.coordinator, "_hub_entry_id", None),
        )
        self.async_on_remove(
            self._event_log_poller.add_listener(self._handle_event_log_result)
        )
        if self.hass.state is CoreState.running:
            self._ha_started = True
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._on_ha_started
            )

    @callback
    def _on_ha_started(self, _event) -> None:
        self._ha_started = True

    @property
    def unique_id(self):
        return super().unique_id + "_poll_latency"

    @property
    def device_class(self) -> Optional[str]:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> Optional[str]:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return UnitOfTime.MILLISECONDS

    @property
    def native_value(self) -> StateType:
        return self._adaptive_state.latency_ms

    @property
    def extra_state_attributes(self):
        return {
            "ema_latency_ms": round(self._adaptive_state.ema_ms, 1)
            if self._adaptive_state.ema_ms
            else None,
            "ema_jitter_ms": round(self._adaptive_state.ema_jitter_ms, 1)
            if self._adaptive_state.ema_jitter_ms
            else None,
            "computed_interval_ms": round(self._adaptive_state.computed_interval_ms, 1)
            if self._adaptive_state.computed_interval_ms
            else None,
            "utilization": round(
                self._adaptive_state.ema_ms / self._adaptive_state.computed_interval_ms,
                3,
            )
            if self._adaptive_state.ema_ms and self._adaptive_state.computed_interval_ms
            else None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self._ha_started or not self.enabled:
            return
        if self._event_log_poller is None:
            self._event_log_poller = get_hub_event_log_poller(
                self.hass,
                self.coordinator,
                self._device,
                getattr(self.coordinator, "_hub_entry_id", None),
            )
        self._event_log_poller.schedule_refresh()
        self.async_write_ha_state()

    @callback
    def _handle_event_log_result(self, result: EventLogPollResult | None) -> None:
        if not self.enabled:
            return
        if result is None:
            self.async_write_ha_state()
            return
        self.async_write_ha_state()

    async def _measure_latency(self) -> None:
        try:
            _, latency_ms = await fetch_event_logs(
                self.coordinator,
                self._device,
                hass=self.hass,
                entry_id=getattr(self.coordinator, "_hub_entry_id", None),
            )
        except Exception:
            self.async_write_ha_state()
            return

        self.async_write_ha_state()

    @property
    def _adaptive_state(self) -> AdaptivePollingState:
        state = getattr(self.coordinator, "_adaptive_polling_state", None)
        if state is None:
            state = AdaptivePollingState()
            self.coordinator._adaptive_polling_state = state
        return state
