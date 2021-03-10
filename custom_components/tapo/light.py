from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.light import (
    LightEntity,
    SUPPORT_BRIGHTNESS,
    ATTR_BRIGHTNESS,
)
from plugp100 import TapoDeviceState

from . import TapoUpdateCoordinator
from .tapo_entity import TapoEntity
from .const import DOMAIN, SUPPORTED_DEVICE_AS_LIGHT


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_LIGHT:
        light = TapoLight(coordinator, entry)
        async_add_devices([light], True)


class TapoLight(TapoEntity, LightEntity):
    @property
    def is_on(self):
        return self._tapo_coordinator.data.device_on

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS  # TODO: return supported feature starting from model type

    @property
    def brightness(self):
        return (self._tapo_coordinator.data.brightness / 100) * 255

    async def async_turn_on(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._change_brightness(kwargs.get(ATTR_BRIGHTNESS, 255))
        await self._tapo_coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = (new_brightness / 255) * 100

        async def _set_brightness():
            await self._tapo_coordinator.api.set_brightness(brightness_to_set)

        await self._execute_with_fallback(_set_brightness)
