from plugp100.components.battery import BatteryComponent
from plugp100.components.motion_sensor import MotionSensorComponent
from plugp100.components.smart_door import SmartDoorComponent
from plugp100.components.water_leak import WaterLeakComponent

from custom_components.tapo.hub.binary_sensor import COMPONENT_MAPPING


class TestSensorMappings:
    def test_binary_sensor_mappings(self):
        expected_mappings = {
            SmartDoorComponent: "SmartDoorSensor",
            WaterLeakComponent: "WaterLeakSensor",
            MotionSensorComponent: "MotionSensor",
            BatteryComponent: "LowBatterySensor",
        }

        assert COMPONENT_MAPPING == expected_mappings
