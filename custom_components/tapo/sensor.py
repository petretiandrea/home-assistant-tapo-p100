from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from custom_components.tapo import HassTapoDeviceData
from custom_components.tapo.common_setup import (
    TapoCoordinator,
    setup_tapo_coordinator_from_dictionary,
)
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)
from custom_components.tapo.coordinators import PlugTapoCoordinator, TapoCoordinator
from custom_components.tapo.sensors import (
    CurrentEnergySensorSource,
    MonthEnergySensorSource,
    MonthRuntimeSensorSource,
    SignalSensorSource,
    TodayEnergySensorSource,
    TodayRuntimeSensorSource,
)
from custom_components.tapo.sensors.tapo_sensor_source import TapoSensorSource
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.utils import get_short_model, value_or_raise

### Supported sensors: Today energy and current power
SUPPORTED_SENSOR = [
    CurrentEnergySensorSource,
    TodayEnergySensorSource,
    MonthEnergySensorSource,
    TodayRuntimeSensorSource,
    MonthRuntimeSensorSource,
    # TapoThisMonthEnergySensor, hotfix
]


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    coordinator = value_or_raise(
        await setup_tapo_coordinator_from_dictionary(hass, config)
    )
    _setup_from_coordinator(coordinator, async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    # get tapo helper
    data: HassTapoDeviceData = hass.data[DOMAIN][entry.entry_id]
    _setup_from_coordinator(data.coordinator, async_add_devices)


def _setup_from_coordinator(
    coordinator: TapoCoordinator, async_add_devices: AddEntitiesCallback
):
    sensors = [TapoSensor(coordinator, SignalSensorSource())]

    if isinstance(coordinator, PlugTapoCoordinator):
        if (
            get_short_model(coordinator.get_device_info().model)
            in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR
        ):
            coordinator.enable_power_monitor()
            sensors.extend(
                [TapoSensor(coordinator, factory()) for factory in SUPPORTED_SENSOR]
            )

    async_add_devices(sensors, True)


class TapoSensor(TapoEntity[Any], SensorEntity):
    def __init__(
        self,
        coordinator: TapoCoordinator[Any],
        sensor_source: TapoSensorSource,
    ):
        super().__init__(coordinator)
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
    def native_value(self) -> Union[StateType, date, datetime]:
        return self._sensor_source.get_value(self.coordinator.get_sensor_state())
