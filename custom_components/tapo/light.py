import logging
from plugp100 import LightEffectPreset
from typing import Dict, Any, Callable, Optional, Union
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_COLOR_TEMP,
    ColorMode,
    SUPPORT_EFFECT,
    ATTR_EFFECT,
)
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
    color_temperature_mired_to_kelvin as mired_to_kelvin,
)
from custom_components.tapo.utils import clamp
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_LIGHT,
    SUPPORTED_LIGHT_EFFECTS,
)
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.common_setup import (
    TapoCoordinator,
    setup_tapo_coordinator_from_dictionary,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoCoordinator = hass.data[DOMAIN][entry.entry_id]
    _setup_from_coordinator(coordinator, async_add_devices)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: Callable,
    discovery_info=None,
) -> None:
    coordinator = await setup_tapo_coordinator_from_dictionary(hass, config)
    _setup_from_coordinator(coordinator, async_add_entities)


def _setup_from_coordinator(coordinator: TapoCoordinator, async_add_devices):
    for (model, color_modes) in SUPPORTED_DEVICE_AS_LIGHT.items():
        if model.lower() in coordinator.data.model.lower():
            light = TapoLight(
                coordinator,
                color_modes=color_modes,
                supported_effects=SUPPORTED_LIGHT_EFFECTS.get(
                    model.lower(), lambda: []
                )(),
            )
            async_add_devices([light], True)


class TapoLight(TapoEntity, LightEntity):
    def __init__(
        self,
        coordinator,
        color_modes: set[ColorMode],
        supported_effects: list[LightEffectPreset] = None,
    ):
        super().__init__(coordinator)
        self._color_modes = color_modes
        self._max_kelvin = 6500
        self._min_kelvin = 2500
        self._max_merids = kelvin_to_mired(2500)
        self._min_merids = kelvin_to_mired(6500)
        self._effects = {effect.name: effect.effect for effect in supported_effects}

    @property
    def is_on(self):
        return self.last_state.device_on

    @property
    def supported_features(self) -> Optional[int]:
        return SUPPORT_EFFECT if self._effects else 0

    @property
    def supported_color_modes(self) -> Union[set[ColorMode], set[str], None]:
        return self._color_modes

    @property
    def brightness(self):
        return round((self.last_state.brightness * 255) / 100)

    @property
    def hs_color(self):
        hue = self.last_state.hue
        saturation = self.last_state.saturation
        if hue and saturation:
            return hue, saturation

    @property
    def color_temp(self):
        color_temp = self.last_state.color_temp
        if color_temp and color_temp > 0:
            return kelvin_to_mired(color_temp)

    @property
    def max_mireds(self):
        return self._max_merids

    @property
    def min_mireds(self):
        return self._min_merids

    @property
    def effect_list(self) -> Optional[list[str]]:
        return list(self._effects.keys()) if self._effects else None

    @property
    def effect(self) -> Optional[str]:
        if (
            self._effects
            and self.last_state.light_effect is not None
            and self.last_state.light_effect.enable
        ):
            return self.last_state.light_effect.name.lower()
        else:
            return None

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color = kwargs.get(ATTR_HS_COLOR)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)
        effect = kwargs.get(ATTR_EFFECT)

        _LOGGER.info("Setting brightness: %s", str(brightness))
        _LOGGER.info("Setting color: %s", str(color))
        _LOGGER.info("Setting color_temp: %s", str(color_temp))
        _LOGGER.info("Setting effect: %s", str(effect))

        if brightness or color or color_temp or effect:
            if self.is_on is False:
                await self._execute_with_fallback(self._tapo_coordinator.api.on)
            if color and ColorMode.HS in self.supported_color_modes:
                hue = int(color[0])
                saturation = int(color[1])
                await self._change_color([hue, saturation], None)
            elif color_temp and ColorMode.COLOR_TEMP in self.supported_color_modes:
                color_temp = int(color_temp)
                await self._change_color_temp(color_temp)
            if brightness:
                await self._change_brightness(brightness)
            if effect:
                await self._tapo_coordinator.api.set_light_effect(self._effects[effect])
        else:
            await self._execute_with_fallback(self._tapo_coordinator.api.on)

        await self._tapo_coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_request_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = round((new_brightness / 255) * 100)
        _LOGGER.debug("Change brightness to: %s", str(brightness_to_set))

        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_brightness(brightness_to_set)
        )

    async def _change_color_temp(self, color_temp):
        _LOGGER.debug("Change color temp to: %s", str(color_temp))
        constraint_color_temp = clamp(color_temp, self._min_merids, self._max_merids)
        kelvin_color_temp = clamp(
            mired_to_kelvin(constraint_color_temp),
            min_value=self._min_kelvin,
            max_value=self._max_kelvin,
        )

        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_color_temperature(
                kelvin_color_temp, self.last_state.brightness
            )
        )

    async def _change_color(self, hs_color, brightness):
        _LOGGER.debug("Change colors to: %s", str(hs_color))

        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_hue_saturation(
                hs_color[0], hs_color[1], brightness
            )
        )
