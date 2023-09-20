from typing import cast

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.binary_sensor import (
    async_setup_entry as async_setup_binary_sensors,
)
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator
from custom_components.tapo.sensor import TapoSensor
from custom_components.tapo.sensors import OverheatSensorSource
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    sensors = [TapoSensor(data.coordinator, OverheatSensorSource())]
    async_add_devices(sensors, True)
    if isinstance(data.coordinator, TapoHubCoordinator):
        await async_setup_binary_sensors(hass, entry, async_add_devices)
