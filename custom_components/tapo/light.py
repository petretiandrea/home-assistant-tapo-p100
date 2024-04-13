import logging
from typing import Optional
from typing import cast

from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.light import ATTR_COLOR_TEMP
from homeassistant.components.light import ATTR_EFFECT
from homeassistant.components.light import ATTR_HS_COLOR
from homeassistant.components.light import ColorMode
from homeassistant.components.light import LightEntity
from homeassistant.components.light import LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
)
from plugp100.api.light_effect_preset import LightEffectPreset
from plugp100.new.components.light_effect_component import LightEffectComponent
from plugp100.new.tapobulb import TapoBulb

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.helpers import hass_to_tapo_brightness
from custom_components.tapo.helpers import hass_to_tapo_color_temperature
from custom_components.tapo.helpers import tapo_to_hass_brightness
from custom_components.tapo.helpers import tapo_to_hass_color_temperature

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if isinstance(data.device, TapoBulb):
        light = TapoLightEntity(data.coordinator, data.device)
        async_add_entities([light], True)


class TapoLightEntity(CoordinatedTapoEntity, LightEntity):
    device: TapoBulb

    def __init__(self, coordinator: TapoDataCoordinator, device: TapoBulb):
        super().__init__(coordinator, device)
        supported_effects = _components_to_light_effects(device)
        self._effects = {effect.name.lower(): effect for effect in supported_effects}
        # set homeassistant light entity attributes
        self._attr_max_color_temp_kelvin = 6500
        self._attr_min_color_temp_kelvin = 2500
        self._attr_max_mireds = kelvin_to_mired(self._attr_min_color_temp_kelvin)
        self._attr_min_mireds = kelvin_to_mired(self._attr_max_color_temp_kelvin)
        self._attr_supported_features = (
            LightEntityFeature.EFFECT if self._effects else 0
        )
        self._attr_supported_color_modes = _components_to_color_modes(device)
        self._attr_effect_list = list(self._effects.keys()) if self._effects else None
        self._is_lightstrip = device.is_led_strip

    @property
    def color_mode(self) -> ColorMode | str | None:
        if ColorMode.HS in self.supported_color_modes and self.hs_color is not None:
            return ColorMode.HS
        elif ColorMode.COLOR_TEMP in self.supported_color_modes and self.color_temp is not None:
            return ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in self.supported_color_modes and self.brightness is not None:
            return ColorMode.BRIGHTNESS
        elif ColorMode.ONOFF in self.supported_color_modes:
            return ColorMode.ONOFF
        else:
            return ColorMode.UNKNOWN

    @property
    def is_on(self):
        return self.device.is_on

    @property
    def brightness(self):
        return tapo_to_hass_brightness(self.device.brightness)

    @property
    def hs_color(self):
        (hue, saturation) = (self.device.hs.hue, self.device.hs.saturation)
        color_temp = self.device.color_temp
        if (
                color_temp is None or color_temp <= 0
        ):  # returns None if color_temp is not set
            if hue is not None and saturation is not None:
                return hue, saturation

    @property
    def color_temp(self):
        return tapo_to_hass_color_temperature(
            self.device.color_temp, (self.min_mireds, self.max_mireds)
        )

    @property
    def effect(self) -> Optional[str]:
        if effect := self.device.effect:
            if effect.enable:
                return effect.name.lower()
        else:
            return None

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color = kwargs.get(ATTR_HS_COLOR)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)
        effect = kwargs.get(ATTR_EFFECT)
        tapo_brightness = hass_to_tapo_brightness(brightness)
        tapo_color_temp = hass_to_tapo_color_temperature(
            color_temp,
            (self.min_mireds, self.max_mireds),
            (self.min_color_temp_kelvin, self.max_color_temp_kelvin),
        )

        _LOGGER.info(
            "Setting brightness: %s, tapo %s", str(brightness), str(tapo_brightness)
        )
        _LOGGER.info("Setting color: %s, tapo %s", str(color), str(color))
        _LOGGER.info(
            "Setting color_temp: %s, tapo %s", str(color_temp), str(tapo_color_temp)
        )
        _LOGGER.info("Setting effect: %s", str(effect))

        await self._set_state(
            on=True,
            color_temp=tapo_color_temp,
            hue_saturation=color,
            brightness=tapo_brightness,
            effect=effect,
            current_effect=self.effect,
        )

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._set_state(on=False)
        await self.coordinator.async_request_refresh()

    async def _set_state(
            self,
            on: bool,
            color_temp=None,
            hue_saturation=None,
            brightness=None,
            effect: str = None,
            current_effect: str = None,
    ):
        if not on:
            return (await self.device.turn_off()).get_or_raise()

        (await self.device.turn_on()).get_or_raise()
        if effect is not None:
            (
                await self.device.set_light_effect(
                    self._effects[effect.lower()].to_effect()
                )
            ).get_or_raise()
        elif hue_saturation is not None and ColorMode.HS in self.supported_color_modes:
            hue = int(hue_saturation[0])
            saturation = int(hue_saturation[1])
            (
                await self.device.set_hue_saturation(hue, saturation)
            ).get_or_raise()
        elif (
                color_temp is not None
                and ColorMode.COLOR_TEMP in self.supported_color_modes
        ):
            color_temp = int(color_temp)
            (
                await self.device.set_color_temperature(color_temp)
            ).get_or_raise()

        # handle all brightness user use cases
        # 1. brightness set with effect (scene)
        # 2. brightness set with colors (scene)
        # 3. brightness set with slider, so change effect or color based on last state
        if brightness is not None:
            if effect is not None:
                await self._change_brightness(brightness, apply_to_effect=effect)
            elif color_temp is not None or hue_saturation is not None:
                await self._change_brightness(brightness, apply_to_effect=None)
            else:
                await self._change_brightness(
                    brightness, apply_to_effect=current_effect
                )

    async def _change_brightness(self, new_brightness, apply_to_effect: str = None):
        if apply_to_effect:
            (
                await self.device.set_light_effect_brightness(
                    self._effects[apply_to_effect.lower()].to_effect(), new_brightness
                )
            ).get_or_raise()
        else:
            (
                await self.device.set_brightness(new_brightness)
            ).get_or_raise()


# follows https://developers.home-assistant.io/docs/core/entity/light/#color-modes
def _components_to_color_modes(device: TapoBulb) -> set[ColorMode]:
    color_modes = []
    if device.is_color_temperature:
        color_modes.append(ColorMode.COLOR_TEMP)
    if device.is_color:
        color_modes.append(ColorMode.HS)
    if device.is_brightness and not device.is_color_temperature and not device.is_color:
        color_modes.append(ColorMode.BRIGHTNESS)
    if not color_modes:
        color_modes.append(ColorMode.ONOFF)
    return set(color_modes)


def _components_to_light_effects(device: TapoBulb):
    if device.has_component(LightEffectComponent):
        return LightEffectPreset
    return []
