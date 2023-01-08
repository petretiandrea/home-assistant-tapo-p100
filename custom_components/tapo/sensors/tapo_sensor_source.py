from typing import Optional
from plugp100 import TapoDeviceState
from homeassistant.helpers.typing import StateType
from custom_components.tapo.sensors.sensor_config import SensorConfig


class TapoSensorSource:
    def get_config(self) -> SensorConfig:
        pass

    def get_value(self, state: Optional[TapoDeviceState]) -> StateType:
        pass
