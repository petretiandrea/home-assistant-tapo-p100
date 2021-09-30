from dataclasses import dataclass
import enum
from typing import Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.components.sensor import (
    STATE_CLASS_TOTAL_INCREASING,
)
from homeassistant.const import (
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
)
from homeassistant.helpers.typing import StateType
from . import TapoUpdateCoordinator
from .tapo_entity import TapoEntity


@dataclass
class SensorConfig:
    name: str
    device_class: str
    state_class: str
    unit_measure: str


class TapoSensor(TapoEntity, SensorEntity):
    def __init__(
        self,
        coordiantor: TapoUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_config: SensorConfig,
    ):
        super().__init__(coordiantor, config_entry)
        self.sensor_config = sensor_config

    @property
    def icon(self) -> str:
        return "mdi:power"

    @property
    def unique_id(self):
        return super().unique_id + "_" + self.sensor_config.name.replace(" ", "_")

    @property
    def name(self):
        return super().name + " " + self.sensor_config.name

    @property
    def device_class(self) -> Optional[str]:
        return self.sensor_config.device_class

    @property
    def state_class(self) -> Optional[str]:
        return self.sensor_config.state_class

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self.sensor_config.unit_measure


class TapoTodayEnergySensor(TapoSensor):
    def __init__(
        self,
        coordiantor: TapoUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        super().__init__(
            coordiantor,
            config_entry,
            SensorConfig(
                "today energy",
                DEVICE_CLASS_ENERGY,
                STATE_CLASS_TOTAL_INCREASING,
                ENERGY_KILO_WATT_HOUR,
            ),
        )

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data.energy_info != None:
            return self.coordinator.data.energy_info.today_energy / 1000
        else:
            return None


class TapoCurrentEnergySensor(TapoSensor):
    def __init__(self, coordiantor: TapoUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(
            coordiantor,
            config_entry,
            SensorConfig(
                "current energy",
                DEVICE_CLASS_POWER,
                STATE_CLASS_MEASUREMENT,
                POWER_WATT,
            ),
        )

    @property
    def native_value(self) -> StateType:
        ## TODO: to be implemented by plugp100
        return None
