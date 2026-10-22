from types import SimpleNamespace
from unittest.mock import MagicMock

from plugp100.components.battery import BatteryComponent
from plugp100.components.motion_sensor import MotionSensorComponent
from plugp100.components.smart_door import SmartDoorComponent
from plugp100.components.water_leak import WaterLeakComponent
import pytest

from custom_components.tapo.hub.binary_sensor import COMPONENT_MAPPING, WaterLeakSensor


class TestSensorMappings:
    def test_binary_sensor_mappings(self):
        expected_mappings = {
            SmartDoorComponent: "SmartDoorSensor",
            WaterLeakComponent: "WaterLeakSensor",
            MotionSensorComponent: "MotionSensor",
            BatteryComponent: "LowBatterySensor",
        }

        assert COMPONENT_MAPPING == expected_mappings


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("normal", False),
        ("water_dry", False),
        ("water_leak", True),
        ("unexpected", True),
    ],
)
def test_water_leak_sensor_state(status: str, expected: bool):
    sensor = WaterLeakSensor.__new__(WaterLeakSensor)
    sensor.device = MagicMock()
    sensor.device.get_component.return_value = SimpleNamespace(
        water_leak_status=status
    )

    assert sensor.is_on is expected
