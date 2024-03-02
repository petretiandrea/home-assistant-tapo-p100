from unittest.mock import Mock

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.sensor import BatteryLevelSensor
from custom_components.tapo.hub.sensor import HumitidySensor
from custom_components.tapo.hub.sensor import ReportIntervalDiagnostic
from custom_components.tapo.hub.sensor import SENSOR_MAPPING
from custom_components.tapo.hub.sensor import TemperatureSensor
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.water_leak_device import WaterLeakSensor as WaterLeakDevice


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_binary_sensor_mappings(self):
        expected_mappings = {
            T31Device: [HumitidySensor, TemperatureSensor, ReportIntervalDiagnostic],
            T110SmartDoor: [ReportIntervalDiagnostic],
            S200ButtonDevice: [ReportIntervalDiagnostic],
            T100MotionSensor: [ReportIntervalDiagnostic],
            WaterLeakDevice: [ReportIntervalDiagnostic],
            KE100Device: [TemperatureSensor, BatteryLevelSensor],
        }

        assert SENSOR_MAPPING == expected_mappings


class TestBatteryLevelSensor:
    coordinator = Mock(TapoDataCoordinator)

    def test_unique_id(self):
        base_data = Mock()
        base_data.base_info.device_id = "hub1234"
        self.coordinator.get_state_of.return_value = base_data

        subject = BatteryLevelSensor(coordinator=self.coordinator)

        result = subject.unique_id

        assert result == "hub1234_Battery_Percentage"

    def test_device_class(self):
        subject = BatteryLevelSensor(coordinator=self.coordinator)

        result = subject.device_class

        assert result == SensorDeviceClass.BATTERY

    def test_state_class(self):
        subject = BatteryLevelSensor(coordinator=self.coordinator)

        result = subject.state_class

        assert result == SensorStateClass.MEASUREMENT

    def test_native_unit_of_measurement(self):
        subject = BatteryLevelSensor(coordinator=self.coordinator)

        result = subject.native_unit_of_measurement

        assert result == PERCENTAGE

    def test_native_value(self):
        base_data = Mock()
        base_data.battery_percentage = 20
        self.coordinator.get_state_of.return_value = base_data

        subject = BatteryLevelSensor(coordinator=self.coordinator)

        result = subject.native_value

        assert result == 20
