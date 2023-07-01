from typing import Optional
from homeassistant.helpers.typing import StateType
from custom_components.tapo.sensors.sensor_config import SensorConfig
from custom_components.tapo.coordinators import SensorState


class TapoSensorSource:
    def get_config(self) -> SensorConfig:
        pass

    def get_value(self, state: Optional[SensorState]) -> StateType:
        pass
