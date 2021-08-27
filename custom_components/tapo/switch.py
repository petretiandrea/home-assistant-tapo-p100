from typing import Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import DEVICE_CLASS_ENERGY, STATE_CLASS_MEASUREMENT
from plugp100 import TapoDeviceState

from . import TapoUpdateCoordinator
from .tapo_entity import TapoEntity
from .const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH:
        switch = P100Switch(coordinator, entry)
        async_add_devices([switch], True)


class P100Switch(TapoEntity, SwitchEntity):
    @property
    def is_on(self):
        return self._tapo_coordinator.data.device_on

    async def async_turn_on(self):
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._tapo_coordinator.async_request_refresh()

    async def async_turn_off(self):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_request_refresh()
