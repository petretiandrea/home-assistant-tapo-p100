from typing import Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    STATE_CLASS_TOTAL_INCREASING,
)
from homeassistant.helpers.typing import StateType

from . import TapoUpdateCoordinator
from .tapo_entity import TapoEntity
from .const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)

SENSOR_NAME_SUFFIX = "today energy"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR:
        energy_sensor = TapoTodayEnergySensor(coordinator, entry)
        async_add_devices([energy_sensor], True)


class TapoTodayEnergySensor(TapoEntity, SensorEntity):
    @property
    def icon(self) -> str:
        return "mdi:power"

    @property
    def unique_id(self):
        return super().unique_id + "_" + SENSOR_NAME_SUFFIX.replace(" ", "_")

    @property
    def name(self):
        return super().name + " " + SENSOR_NAME_SUFFIX

    @property
    def device_class(self) -> Optional[str]:
        return DEVICE_CLASS_ENERGY

    @property
    def state_class(self) -> Optional[str]:
        return STATE_CLASS_TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return "kWh"

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data.energy_info != None:
            return self.coordinator.data.energy_info.today_energy / 1000
        else:
            return None
