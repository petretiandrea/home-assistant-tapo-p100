import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
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
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.new.child.tapohubchildren import TriggerButtonDevice
from plugp100.new.components.battery_component import BatteryComponent
from plugp100.new.components.humidity_component import HumidityComponent
from plugp100.new.components.report_mode_component import ReportModeComponent
from plugp100.new.components.temperature_component import TemperatureComponent
from plugp100.new.components.trigger_log_component import TriggerLogComponent
from plugp100.new.tapodevice import TapoDevice
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.hub.event import fetch_event_logs

_LOGGER = logging.getLogger(__name__)

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

        if isinstance(child_coordinator.device, TriggerButtonDevice) and \
                child_coordinator.device.has_component(TriggerLogComponent):
            sensors.append(PollLatencySensor(child_coordinator, child_coordinator.device))

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


class PollLatencySensor(CoordinatedTapoEntity, SensorEntity):
    """Measures poll latency and adaptively tunes the polling interval.

    Budget-based utilization control:
      interval = clamp((L + 2*J) / u_max, I_min, I_max)
    where L = EWMA of latency, J = EWMA of jitter (absolute deviation).
    This keeps request utilization (latency/interval) at or below u_max.

    Hysteresis prevents thrashing: interval only changes when the target
    differs from current by more than HYSTERESIS_PCT, and not more often
    than every COOLDOWN_CYCLES cycles.
    """

    _attr_has_entity_name = True
    _attr_name = "Poll Latency"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:connection"

    # Smoothing
    EMA_ALPHA = 0.3          # EWMA smoothing factor (higher = more reactive)
    # Budget
    DEFAULT_U_MAX = 0.35     # fallback if number entity hasn't loaded yet
    JITTER_WEIGHT = 2.0      # how much jitter inflates the budget
    # Bounds
    MIN_INTERVAL_MS = 300
    MAX_INTERVAL_MS = 5000
    # Hysteresis
    HYSTERESIS_PCT = 0.15    # ignore target changes smaller than 15%
    COOLDOWN_CYCLES = 5      # minimum cycles between interval adjustments

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TriggerButtonDevice,
    ):
        super().__init__(coordinator, device)
        self._device: TriggerButtonDevice = device
        self._latency_ms: float | None = None
        self._ema_ms: float | None = None
        self._ema_jitter_ms: float | None = None
        self._computed_interval_ms: float | None = None
        self._cycles_since_change: int = 0
        self._ha_started: bool = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
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
    def _u_max(self) -> float:
        """Read utilization target from the PollUtilization number entity via coordinator."""
        pct = getattr(self.coordinator, "_poll_utilization_pct", None)
        if pct is not None:
            return pct / 100.0
        return self.DEFAULT_U_MAX

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
        return self._latency_ms

    @property
    def extra_state_attributes(self):
        return {
            "ema_latency_ms": round(self._ema_ms, 1) if self._ema_ms else None,
            "ema_jitter_ms": round(self._ema_jitter_ms, 1) if self._ema_jitter_ms else None,
            "computed_interval_ms": round(self._computed_interval_ms, 1) if self._computed_interval_ms else None,
            "utilization": round(self._ema_ms / self._computed_interval_ms, 3) if self._ema_ms and self._computed_interval_ms else None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self._ha_started:
            return
        self.hass.async_create_task(self._measure_latency())
        self.async_write_ha_state()

    async def _measure_latency(self) -> None:
        try:
            _, latency_ms = await fetch_event_logs(self.coordinator, self._device)
            self._latency_ms = round(latency_ms, 1)
        except Exception:
            self._latency_ms = None
            self.async_write_ha_state()
            return

        # Bootstrap
        if self._ema_ms is None:
            self._ema_ms = latency_ms
            self._ema_jitter_ms = 0.0
            self._computed_interval_ms = max(
                self.MIN_INTERVAL_MS, latency_ms / self._u_max
            )
            self.coordinator.update_interval = timedelta(milliseconds=self._computed_interval_ms)
            self.async_write_ha_state()
            return

        # Update smoothed latency and jitter
        self._ema_ms = self.EMA_ALPHA * latency_ms + (1 - self.EMA_ALPHA) * self._ema_ms
        jitter = abs(latency_ms - self._ema_ms)
        self._ema_jitter_ms = self.EMA_ALPHA * jitter + (1 - self.EMA_ALPHA) * self._ema_jitter_ms

        # Budget-based target: keep utilization <= U_MAX
        effective_latency = self._ema_ms + self.JITTER_WEIGHT * self._ema_jitter_ms
        target = effective_latency / self._u_max
        target = max(self.MIN_INTERVAL_MS, min(self.MAX_INTERVAL_MS, target))

        # Hysteresis + cooldown: only change if meaningful and not too frequent
        self._cycles_since_change += 1
        pct_change = abs(target - self._computed_interval_ms) / self._computed_interval_ms
        if pct_change > self.HYSTERESIS_PCT and self._cycles_since_change >= self.COOLDOWN_CYCLES:
            self._computed_interval_ms = target
            self._cycles_since_change = 0

        self.coordinator.update_interval = timedelta(milliseconds=self._computed_interval_ms)
        self.async_write_ha_state()
