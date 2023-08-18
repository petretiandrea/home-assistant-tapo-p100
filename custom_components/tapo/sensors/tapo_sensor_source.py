from typing import List, Type, TypeVar
from homeassistant.helpers.typing import StateType

from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.sensors.sensor_config import SensorConfig


class TapoSensorSource:
    def get_config(self) -> SensorConfig:
        pass

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        pass
