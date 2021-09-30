from dataclasses import dataclass
import enum
from typing import Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.helpers.typing import StateType
from . import TapoUpdateCoordinator
from .tapo_sensor_entity import TapoTodayEnergySensor, TapoCurrentEnergySensor
from .const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)

### Supported sensors: Today energy and current energy
SUPPORTED_SENSOR = [TapoTodayEnergySensor, TapoCurrentEnergySensor]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR:
        sensors = [factory(coordinator, entry) for factory in SUPPORTED_SENSOR]
        async_add_devices([sensors], True)
