from datetime import date, datetime
from typing import Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import SensorEntity
from custom_components.tapo.common_setup import TapoCoordinator
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)
from custom_components.tapo.sensors import (
    CurrentEnergySensorSource,
    MonthEnergySensorSource,
    SignalSensorSource,
    TodayEnergySensorSource,
)
from custom_components.tapo.sensors.tapo_sensor_source import TapoSensorSource
from custom_components.tapo.tapo_entity import TapoEntity

### Supported sensors: Today energy and current power
SUPPORTED_SENSOR = [
    CurrentEnergySensorSource,
    TodayEnergySensorSource,
    MonthEnergySensorSource,
    # TapoThisMonthEnergySensor, hotfix
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [TapoSensor(coordinator, SignalSensorSource())]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR:
        sensors.extend(
            [TapoSensor(coordinator, factory()) for factory in SUPPORTED_SENSOR]
        )

    async_add_devices(sensors, True)


class TapoSensor(TapoEntity, SensorEntity):
    def __init__(
        self,
        coordiantor: TapoCoordinator,
        sensor_source: TapoSensorSource,
    ):
        super().__init__(coordiantor)
        self._sensor_source = sensor_source
        self._sensor_config = self._sensor_source.get_config()

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._sensor_config.name.replace(" ", "_")

    @property
    def name(self):
        return super().name + " " + self._sensor_config.name

    @property
    def device_class(self) -> Optional[str]:
        return self._sensor_config.device_class

    @property
    def state_class(self) -> Optional[str]:
        return self._sensor_config.state_class

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self._sensor_config.unit_measure

    @property
    def native_value(self) -> StateType | date | datetime:
        return self._sensor_source.get_value(self.last_state)
