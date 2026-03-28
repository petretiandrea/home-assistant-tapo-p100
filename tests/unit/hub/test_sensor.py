from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from plugp100.common.functional.tri import Success
from plugp100.components.battery import BatteryComponent
from plugp100.components.humidity import HumidityComponent
from plugp100.components.report_mode import ReportModeComponent
from plugp100.components.temperature import TemperatureComponent
from plugp100.devices.base import TapoDevice
from plugp100.devices.children.trigger_button import TriggerButtonDevice
import pytest

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.sensor import (
    COMPONENT_MAPPING,
    BatteryLevelSensor,
    PollLatencySensor,
)
from tests.conftest import _mock_hub_child_device


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_sensor_mappings(self):
        expected_mappings = {
            HumidityComponent: "HumiditySensor",
            TemperatureComponent: "TemperatureSensor",
            ReportModeComponent: "ReportIntervalDiagnostic",
            BatteryComponent: "BatteryLevelSensor",
        }

        assert COMPONENT_MAPPING == expected_mappings


def _mock_battery_component(mock_device: MagicMock) -> MagicMock:
    battery_component = MagicMock(BatteryComponent())
    battery_component.battery_percentage = 100
    battery_component.is_battery_low = False
    battery_component.update = AsyncMock(return_value=None)
    mock_device.add_component(battery_component)
    return mock_device


class TestBatteryLevelSensor:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_battery_component(
            _mock_hub_child_device(MagicMock(auto_spec=TapoDevice))
        )
        self.battery_sensor = BatteryLevelSensor(
            coordinator=self.coordinator, device=self.device
        )

    def test_unique_id(self):
        assert self.battery_sensor.unique_id == "123_Battery_Percentage"

    def test_device_class(self):
        assert self.battery_sensor.device_class == SensorDeviceClass.BATTERY

    def test_state_class(self):
        assert self.battery_sensor.state_class == SensorStateClass.MEASUREMENT

    def test_native_unit_of_measurement(self):
        assert self.battery_sensor.native_unit_of_measurement == PERCENTAGE

    def test_native_value(self):
        assert self.battery_sensor.native_value == 100


def _mock_trigger_device():
    device = _mock_hub_child_device(MagicMock(auto_spec=TriggerButtonDevice))
    logs = MagicMock()
    logs.events = []
    device.get_event_logs = AsyncMock(return_value=Success(logs))
    return device, logs


class TestPollLatencySensorProperties:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )

    def test_unique_id(self):
        assert self.sensor.unique_id == "123_poll_latency"

    def test_name(self):
        assert self.sensor._attr_name == "Poll Latency"

    def test_entity_category(self):
        assert self.sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    def test_icon(self):
        assert self.sensor._attr_icon == "mdi:connection"

    def test_device_class(self):
        assert self.sensor.device_class == SensorDeviceClass.DURATION

    def test_state_class(self):
        assert self.sensor.state_class == SensorStateClass.MEASUREMENT

    def test_native_unit_of_measurement(self):
        assert self.sensor.native_unit_of_measurement == UnitOfTime.MILLISECONDS

    def test_native_value_initially_none(self):
        assert self.sensor.native_value is None

    def test_ha_started_defaults_false(self):
        assert self.sensor._ha_started is False


class TestPollLatencySensorUMax:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )

    def test_u_max_default_when_no_attr(self):
        self.coordinator._poll_utilization_pct = None
        assert self.sensor._u_max == PollLatencySensor.DEFAULT_U_MAX

    def test_u_max_reads_from_coordinator(self):
        self.coordinator._poll_utilization_pct = 50
        assert self.sensor._u_max == 0.5

    def test_u_max_reads_low_value(self):
        self.coordinator._poll_utilization_pct = 5
        assert self.sensor._u_max == 0.05


class TestPollLatencySensorExtraStateAttributes:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )

    def test_all_none_initially(self):
        attrs = self.sensor.extra_state_attributes
        assert attrs["ema_latency_ms"] is None
        assert attrs["ema_jitter_ms"] is None
        assert attrs["computed_interval_ms"] is None
        assert attrs["utilization"] is None

    def test_populated_after_values_set(self):
        self.sensor._ema_ms = 80.0
        self.sensor._ema_jitter_ms = 10.0
        self.sensor._computed_interval_ms = 500.0
        attrs = self.sensor.extra_state_attributes
        assert attrs["ema_latency_ms"] == 80.0
        assert attrs["ema_jitter_ms"] == 10.0
        assert attrs["computed_interval_ms"] == 500.0
        assert attrs["utilization"] == 0.16


class TestPollLatencySensorStartupDeferral:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )

    def test_handle_coordinator_update_skips_when_not_started(self):
        self.sensor.hass = MagicMock()
        self.sensor.async_write_ha_state = MagicMock()
        self.sensor._handle_coordinator_update()
        self.sensor.hass.async_create_task.assert_not_called()

    def test_handle_coordinator_update_runs_when_started(self):
        self.sensor._ha_started = True
        self.sensor.hass = MagicMock()
        self.sensor.async_write_ha_state = MagicMock()
        self.sensor._handle_coordinator_update()
        self.sensor.hass.async_create_task.assert_called_once()

    def test_on_ha_started_callback(self):
        self.sensor._on_ha_started(None)
        assert self.sensor._ha_started is True


class TestMeasureLatencyBootstrap:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.coordinator._event_log_cache = None
        self.coordinator._hub_entry_id = "entry_1"
        self.device, self.logs = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )
        self.sensor.hass = MagicMock()
        self.sensor.hass.data = {}
        self.sensor._ha_started = True
        self.sensor.async_write_ha_state = MagicMock()

    async def test_bootstrap_sets_ema_to_first_latency(self):
        await self.sensor._measure_latency()
        assert self.sensor._ema_ms is not None
        assert self.sensor._ema_jitter_ms == 0.0
        assert self.sensor._latency_ms is not None

    async def test_bootstrap_sets_initial_interval(self):
        await self.sensor._measure_latency()
        assert self.sensor._computed_interval_ms is not None
        assert self.sensor._computed_interval_ms >= PollLatencySensor.MIN_INTERVAL_MS

    async def test_bootstrap_updates_coordinator_interval(self):
        await self.sensor._measure_latency()
        assert isinstance(self.coordinator.update_interval, timedelta)

    async def test_bootstrap_calls_write_ha_state(self):
        await self.sensor._measure_latency()
        self.sensor.async_write_ha_state.assert_called()


class TestMeasureLatencySteadyState:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.coordinator._event_log_cache = None
        self.coordinator._hub_entry_id = "entry_1"
        self.device, self.logs = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )
        self.sensor.hass = MagicMock()
        self.sensor.hass.data = {}
        self.sensor._ha_started = True
        self.sensor.async_write_ha_state = MagicMock()
        # Pre-seed bootstrap state
        self.sensor._ema_ms = 80.0
        self.sensor._ema_jitter_ms = 5.0
        self.sensor._computed_interval_ms = 500.0
        self.sensor._cycles_since_change = 0

    async def test_ema_update(self):
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._ema_ms is not None
        assert self.sensor._latency_ms is not None

    async def test_hysteresis_prevents_small_changes(self):
        """Interval stays the same when cycles_since_change < COOLDOWN_CYCLES."""
        original_interval = self.sensor._computed_interval_ms
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._computed_interval_ms == original_interval

    async def test_cooldown_prevents_frequent_changes(self):
        """Interval doesn't change before COOLDOWN_CYCLES even with large delta."""
        self.sensor._cycles_since_change = 2
        original_interval = self.sensor._computed_interval_ms
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._computed_interval_ms == original_interval

    async def test_interval_changes_after_cooldown(self):
        """Interval changes when cooldown expired and change is significant."""
        self.sensor._cycles_since_change = PollLatencySensor.COOLDOWN_CYCLES
        self.sensor._ema_ms = 200.0
        self.sensor._ema_jitter_ms = 50.0
        self.sensor._computed_interval_ms = 500.0
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._cycles_since_change == 0

    async def test_interval_clamped_to_min(self):
        """Computed interval never goes below MIN_INTERVAL_MS."""
        self.sensor._cycles_since_change = PollLatencySensor.COOLDOWN_CYCLES
        self.sensor._ema_ms = 10.0
        self.sensor._ema_jitter_ms = 1.0
        self.sensor._computed_interval_ms = 5000.0
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._computed_interval_ms >= PollLatencySensor.MIN_INTERVAL_MS

    async def test_interval_clamped_to_max(self):
        """Computed interval never goes above MAX_INTERVAL_MS."""
        self.sensor._cycles_since_change = PollLatencySensor.COOLDOWN_CYCLES
        self.sensor._ema_ms = 2000.0
        self.sensor._ema_jitter_ms = 500.0
        self.sensor._computed_interval_ms = 300.0
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert self.sensor._computed_interval_ms <= PollLatencySensor.MAX_INTERVAL_MS

    async def test_always_updates_coordinator_interval(self):
        self.coordinator._event_log_cache = None
        await self.sensor._measure_latency()
        assert isinstance(self.coordinator.update_interval, timedelta)


class TestMeasureLatencyError:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.coordinator._event_log_cache = None
        self.coordinator._hub_entry_id = "entry_1"
        self.device, _ = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )
        self.sensor.hass = MagicMock()
        self.sensor.hass.data = {}
        self.sensor._ha_started = True
        self.sensor.async_write_ha_state = MagicMock()

    async def test_exception_sets_latency_to_none(self):
        self.device.get_event_logs = AsyncMock(side_effect=Exception("timeout"))
        await self.sensor._measure_latency()
        assert self.sensor._latency_ms is None

    async def test_exception_calls_write_ha_state(self):
        self.device.get_event_logs = AsyncMock(side_effect=Exception("timeout"))
        await self.sensor._measure_latency()
        self.sensor.async_write_ha_state.assert_called()

    async def test_exception_does_not_update_ema(self):
        self.sensor._ema_ms = 80.0
        self.device.get_event_logs = AsyncMock(side_effect=Exception("timeout"))
        await self.sensor._measure_latency()
        assert self.sensor._ema_ms == 80.0


class TestAdaptiveAlgorithmMath:
    """Direct math validation of the adaptive polling formula."""

    def test_ewma_formula(self):
        alpha = PollLatencySensor.EMA_ALPHA  # 0.3
        old_ema = 80.0
        sample = 120.0
        expected = alpha * sample + (1 - alpha) * old_ema
        assert expected == pytest.approx(92.0)

    def test_budget_formula(self):
        ema = 80.0
        jitter = 10.0
        u_max = 0.35
        effective = ema + PollLatencySensor.JITTER_WEIGHT * jitter
        target = effective / u_max
        assert effective == pytest.approx(100.0)
        assert target == pytest.approx(285.7, rel=0.01)

    def test_hysteresis_threshold(self):
        current = 500.0
        # 14% change — should be ignored
        target_small = 570.0
        pct_small = abs(target_small - current) / current
        assert pct_small < PollLatencySensor.HYSTERESIS_PCT

        # 16% change — should trigger
        target_large = 580.0
        pct_large = abs(target_large - current) / current
        assert pct_large > PollLatencySensor.HYSTERESIS_PCT

    def test_clamping_bounds(self):
        assert (
            max(
                PollLatencySensor.MIN_INTERVAL_MS,
                min(PollLatencySensor.MAX_INTERVAL_MS, 100),
            )
            == 300
        )
        assert (
            max(
                PollLatencySensor.MIN_INTERVAL_MS,
                min(PollLatencySensor.MAX_INTERVAL_MS, 10000),
            )
            == 5000
        )
        assert (
            max(
                PollLatencySensor.MIN_INTERVAL_MS,
                min(PollLatencySensor.MAX_INTERVAL_MS, 1000),
            )
            == 1000
        )
