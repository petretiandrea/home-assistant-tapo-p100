from plugp100.new.components.battery_component import BatteryComponent
from plugp100.new.components.motion_sensor_component import MotionSensorComponent
from plugp100.new.components.smart_door_component import SmartDoorComponent
from plugp100.new.components.water_leak_component import WaterLeakComponent

from custom_components.tapo.hub.binary_sensor import COMPONENT_MAPPING


class TestSensorMappings:
    def test_binary_sensor_mappings(self):
        expected_mappings = {
            SmartDoorComponent: 'SmartDoorSensor',
            WaterLeakComponent: 'WaterLeakSensor',
            MotionSensorComponent: 'MotionSensor',
            BatteryComponent: 'LowBatterySensor'
        }

        assert COMPONENT_MAPPING == expected_mappings
