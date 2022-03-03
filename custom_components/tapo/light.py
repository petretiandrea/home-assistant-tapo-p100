import logging
from typing import Dict, Any, Callable

from plugp100 import TapoDeviceState
from custom_components.tapo.common_setup import (
    TapoUpdateCoordinator,
    setup_tapo_coordinator_from_dictionary,
)
from custom_components.tapo.utils import clamp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.light import (
    LightEntity,
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
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.const import DOMAIN, SUPPORTED_DEVICE_AS_LIGHT


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _setup_from_coordinator(coordinator, async_add_devices)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: Callable,
    discovery_info=None,
) -> None:
    coordinator = await setup_tapo_coordinator_from_dictionary(hass, config)
    _setup_from_coordinator(coordinator, async_add_entities)


def _setup_from_coordinator(coordinator: TapoUpdateCoordinator, async_add_devices):
    for (model, capabilities) in SUPPORTED_DEVICE_AS_LIGHT.items():
        if model.lower() in coordinator.data.model.lower():
            light = TapoLight(
                coordinator,
                capabilities,
            )
            async_add_devices([light], True)


class TapoLight(TapoEntity, LightEntity):
    def __init__(self, coordinator, features: int):
        super().__init__(coordinator)
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
        return round((self._tapo_coordinator.data.brightness * 255) / 100)

    @property
    def hs_color(self):
        hue = self._tapo_coordinator.data.hue
        saturation = self._tapo_coordinator.data.saturation
        if hue and saturation:
            return hue, saturation

    @property
    def color_temp(self):
        color_temp = self._tapo_coordinator.data.color_temp
        if color_temp and color_temp > 0:
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

        _LOGGER.info(f"Setting brightness: {brightness}")
        _LOGGER.info(f"Setting color: {color}")
        _LOGGER.info(f"Setting color_temp: {color_temp}")

        if brightness or color or color_temp:
            if self.is_on is False:
                await self._execute_with_fallback(self._tapo_coordinator.api.on)
            if brightness:
                await self._change_brightness(brightness)
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
        brightness_to_set = round((new_brightness / 255) * 100)
        _LOGGER.info(f"Mapped brightness: {brightness_to_set}")

        async def _set_brightness():
            await self._tapo_coordinator.api.set_brightness(brightness_to_set)

        await self._execute_with_fallback(_set_brightness)

    async def _change_color_temp(self, color_temp):
        _LOGGER.info(f"Mapped color temp: {color_temp}")
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
        _LOGGER.info(f"Mapped colors: {hs_color}")
        # L530 HW 2 device need to set color_temp to 0 before set hue and saturation.
        # When color_temp > 0 the device will ignore any hue and saturation value
        if (
            await self.is_hardware_v2()
        ) and self.supported_features & SUPPORT_COLOR_TEMP:
            await self._execute_with_fallback(
                lambda: self._tapo_coordinator.api.set_color_temperature(0)
            )

        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_hue_saturation(
                hs_color[0], hs_color[1]
            )
        )

    async def is_hardware_v2(self) -> bool:
        device_state: TapoDeviceState = self.coordinator.data
        hw_version = (
            device_state.state["hw_ver"] if "hw_ver" in device_state.state else None
        )
        return hw_version is not None and hw_version == "2.0"
