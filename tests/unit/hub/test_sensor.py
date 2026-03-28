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
from custom_components.tapo.hub.event import AdaptivePollingState
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
        self.coordinator._adaptive_polling_state = AdaptivePollingState(
            latency_ms=80.0,
            ema_ms=80.0,
            ema_jitter_ms=10.0,
            computed_interval_ms=500.0,
        )
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

    def test_handle_coordinator_update_skips_when_disabled(self):
        self.sensor._ha_started = True
        self.sensor.hass = MagicMock()
        self.sensor.async_write_ha_state = MagicMock()
        self.sensor.registry_entry = MagicMock(disabled=True)
        self.sensor._handle_coordinator_update()
        self.sensor.hass.async_create_task.assert_not_called()
        self.sensor.async_write_ha_state.assert_not_called()

    def test_on_ha_started_callback(self):
        self.sensor._on_ha_started(None)
        assert self.sensor._ha_started is True


class TestPollLatencySensorCoordinatorState:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, self.logs = _mock_trigger_device()
        self.sensor = PollLatencySensor(
            coordinator=self.coordinator, device=self.device
        )
        self.sensor.async_write_ha_state = MagicMock()

    def test_native_value_reads_from_shared_state(self):
        self.coordinator._adaptive_polling_state = AdaptivePollingState(latency_ms=42.5)
        assert self.sensor.native_value == 42.5

    def test_handle_event_log_result_writes_state(self):
        self.coordinator._adaptive_polling_state = AdaptivePollingState(latency_ms=55.5)
        self.sensor._handle_event_log_result(MagicMock(latency_ms=55.5))
        self.sensor.async_write_ha_state.assert_called_once()

    def test_handle_event_log_result_error_leaves_shared_state(self):
        self.coordinator._adaptive_polling_state = AdaptivePollingState(
            latency_ms=80.0, ema_ms=80.0
        )
        self.sensor._handle_event_log_result(None)
        assert self.sensor.native_value == 80.0
        self.sensor.async_write_ha_state.assert_called_once()
