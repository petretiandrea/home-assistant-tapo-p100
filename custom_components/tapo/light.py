from custom_components.tapo.utils import clamp
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
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
    color_temperature_mired_to_kelvin as mired_to_kelvin,
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
            light = TapoLight(
                coordinator,
                entry,
                capabilities,
            )
            async_add_devices([light], True)


class TapoLight(TapoEntity, LightEntity):
    def __init__(self, coordinator, config_entry, features: int):
        super().__init__(coordinator, config_entry)
        self.features = features
        self._max_kelvin = 6500
        self._min_kelvin = 2500
        self._max_merids = kelvin_to_mired(2500)
        self._min_merids = kelvin_to_mired(6500)

    @property
    def is_on(self):
        return self._tapo_coordinator.data.device_on

    @property
    def supported_features(self):
        """Flag supported features."""
        return self.features

    @property
    def brightness(self):
        return (self._tapo_coordinator.data.brightness / 100) * 255

    @property
    def hs_color(self):
        hue = self._tapo_coordinator.data.hue
        saturation = self._tapo_coordinator.data.saturation
        if hue and saturation:
            return hue, saturation

    @property
    def color_temp(self):
        color_temp = self._tapo_coordinator.data.color_temp
        if color_temp:
            return kelvin_to_mired(color_temp)

    @property
    def max_mireds(self):
        return self._max_merids

    @property
    def min_mireds(self):
        return self._min_merids

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color = kwargs.get(ATTR_HS_COLOR)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)

        if brightness or color or color_temp:
            if brightness:
                await self._change_brightness(kwargs.get(ATTR_BRIGHTNESS, 255))
            if color and self.supported_features & SUPPORT_COLOR:
                hue = int(color[0])
                saturation = int(color[1])
                await self._change_color([hue, saturation])
            elif color_temp and self.supported_features & SUPPORT_COLOR_TEMP:
                color_temp = int(color_temp)
                await self._change_color_temp(color_temp)
        else:
            await self._execute_with_fallback(self._tapo_coordinator.api.on)

        await self._tapo_coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_request_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = (new_brightness / 255) * 100

        async def _set_brightness():
            await self._tapo_coordinator.api.set_brightness(brightness_to_set)

        await self._execute_with_fallback(_set_brightness)

    async def _change_color_temp(self, color_temp):
        constraint_color_temp = clamp(color_temp, self._min_merids, self._max_merids)
        kelvin_color_temp = clamp(
            mired_to_kelvin(constraint_color_temp),
            min_value=self._min_kelvin,
            max_value=self._max_kelvin,
        )
        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_color_temperature(kelvin_color_temp)
        )

    async def _change_color(self, hs_color):
        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_hue_saturation(
                hs_color[0], hs_color[1]
            )
        )
