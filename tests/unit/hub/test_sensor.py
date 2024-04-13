from unittest.mock import Mock, MagicMock, AsyncMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE
from plugp100.new.child.tapohubchildren import TapoHubChildDevice
from plugp100.new.components.battery_component import BatteryComponent
from plugp100.new.components.humidity_component import HumidityComponent
from plugp100.new.components.report_mode_component import ReportModeComponent
from plugp100.new.components.temperature_component import TemperatureComponent

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.sensor import BatteryLevelSensor, COMPONENT_MAPPING
from tests.conftest import _mock_hub_child_device


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_sensor_mappings(self):

        expected_mappings = {
            HumidityComponent: 'HumiditySensor',
            TemperatureComponent: 'TemperatureSensor',
            ReportModeComponent: 'ReportIntervalDiagnostic',
            BatteryComponent: 'BatteryLevelSensor'
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
        self.device = _mock_battery_component(_mock_hub_child_device(MagicMock(auto_spec=TapoHubChildDevice)))
        self.battery_sensor = BatteryLevelSensor(coordinator=self.coordinator, device=self.device)

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
