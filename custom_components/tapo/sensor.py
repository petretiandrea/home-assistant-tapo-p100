from datetime import date, datetime
from typing import Any, Dict, Optional, Union, cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)
from custom_components.tapo.coordinators import (
    HassTapoDeviceData,
    PlugTapoCoordinator,
    TapoCoordinator,
)
from custom_components.tapo.entity import BaseTapoEntity
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.sensors import (
    CurrentEnergySensorSource,
    MonthEnergySensorSource,
    MonthRuntimeSensorSource,
    SignalSensorSource,
    TodayEnergySensorSource,
    TodayRuntimeSensorSource,
)
from custom_components.tapo.sensors.tapo_sensor_source import TapoSensorSource
from custom_components.tapo.setup_helpers import setup_from_platform_config

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
    coordinator = await setup_from_platform_config(hass, config)
    _setup_from_coordinator(hass, coordinator, async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    _setup_from_coordinator(hass, data.coordinator, async_add_entities)


def _setup_from_coordinator(
    hass: HomeAssistant,
    coordinator: TapoCoordinator,
    async_add_entities: AddEntitiesCallback,
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

    async_add_entities(sensors, True)


class TapoSensor(BaseTapoEntity[Any], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TapoCoordinator[Any],
        sensor_source: TapoSensorSource,
    ):
        super().__init__(coordinator)
        self._sensor_source = sensor_source
        self._sensor_config = self._sensor_source.get_config()
        self._attr_entity_category = (
            EntityCategory.DIAGNOSTIC if self._sensor_config.is_diagnostic else None
        )

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._sensor_config.name.replace(" ", "_")

    @property
    def name(self):
        return self._sensor_config.name.strip().title()

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
