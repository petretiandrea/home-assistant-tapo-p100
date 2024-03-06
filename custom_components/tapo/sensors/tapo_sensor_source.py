from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.sensors.sensor_config import SensorConfig
from homeassistant.helpers.typing import StateType


class TapoSensorSource:
    def get_config(self) -> SensorConfig:
        pass

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        pass
