from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.light import (
    LightEntity,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_COLOR_TEMP,
)
from typing import List, Optional
from plugp100 import TapoDeviceState

from . import TapoUpdateCoordinator
from .tapo_entity import TapoEntity
from .const import DOMAIN, SUPPORTED_DEVICE_AS_LIGHT


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for (model, capabilities) in SUPPORTED_DEVICE_AS_LIGHT.items():
        if model.lower() in coordinator.data.model.lower():
            light = TapoLight(coordinator, entry, capabilities)
            async_add_devices([light], True)


class TapoLight(TapoEntity, LightEntity):
    def __init__(self, coordinator, config_entry, features: int):
        super().__init__(coordinator, config_entry)
        self.features = features

    @property
    def is_on(self):
        return self._tapo_coordinator.data.device_on

    @property
    def supported_features(self):
        """Flag supported features."""
        return self.features
        # return SUPPORT_BRIGHTNESS  # TODO: return supported feature starting from model type

    @property
    def brightness(self):
        return (self._tapo_coordinator.data.brightness / 100) * 255

    @property
    def hs_color(self):
        hue = self._tapo_coordinator.data.hue
        saturation = self._tapo_coordinator.data.saturation
        return hue, saturation

    @property
    def color_temp(self):
        return self._tapo_coordinator.data.color_temp

    async def async_turn_on(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._change_brightness(kwargs.get(ATTR_BRIGHTNESS, 255))

        if ATTR_HS_COLOR in kwargs:
            hue = int(kwargs.get(ATTR_HS_COLOR)[0])
            saturation = int(kwargs.get(ATTR_HS_COLOR)[1])
            await self._execute_with_fallback(
                lambda: self._tapo_coordinator.api.set_hue_saturation(hue, saturation)
            )
        elif ATTR_COLOR_TEMP in kwargs:
            color_temp = int(kwargs.get(ATTR_COLOR_TEMP))
            await self._execute_with_fallback(
                lambda: self._tapo_coordinator.api.set_color_temperature(color_temp)
            )

        await self._tapo_coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = (new_brightness / 255) * 100

        async def _set_brightness():
            await self._tapo_coordinator.api.set_brightness(brightness_to_set)

        await self._execute_with_fallback(_set_brightness)
