from custom_components.tapo.hub.binary_sensor import LowBatterySensor
from custom_components.tapo.hub.binary_sensor import MotionSensor
from custom_components.tapo.hub.binary_sensor import SENSOR_MAPPING
from custom_components.tapo.hub.binary_sensor import SmartDoorSensor
from custom_components.tapo.hub.binary_sensor import WaterLeakSensor
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.water_leak_device import WaterLeakSensor as WaterLeakDevice


class TestSensorMappings:
    def test_binary_sensor_mappings(self):
        expected_mappings = {
            T31Device: [LowBatterySensor],
            T110SmartDoor: [SmartDoorSensor, LowBatterySensor],
            S200ButtonDevice: [LowBatterySensor],
            T100MotionSensor: [MotionSensor, LowBatterySensor],
            SwitchChildDevice: [LowBatterySensor],
            WaterLeakDevice: [WaterLeakSensor, LowBatterySensor],
            KE100Device: [LowBatterySensor],
        }

        assert SENSOR_MAPPING == expected_mappings
