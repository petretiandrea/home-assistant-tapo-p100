import logging
from typing import Any
from typing import cast
from typing import Dict
from typing import Optional

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_LIGHT
from custom_components.tapo.const import SUPPORTED_LIGHT_EFFECTS
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import LightTapoCoordinator
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.entity import BaseTapoEntity
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.helpers import hass_to_tapo_brightness
from custom_components.tapo.helpers import hass_to_tapo_color_temperature
from custom_components.tapo.helpers import tapo_to_hass_brightness
from custom_components.tapo.helpers import tapo_to_hass_color_temperature
from custom_components.tapo.setup_helpers import setup_from_platform_config
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.light import ATTR_COLOR_TEMP
from homeassistant.components.light import ATTR_EFFECT
from homeassistant.components.light import ATTR_HS_COLOR
from homeassistant.components.light import ColorMode
from homeassistant.components.light import LightEntity
from homeassistant.components.light import SUPPORT_EFFECT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
)
from plugp100.api.light_effect_preset import LightEffectPreset

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    coordinator = await setup_from_platform_config(hass, config)
    _setup_from_coordinator(hass, coordinator, async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    _setup_from_coordinator(hass, data.coordinator, async_add_entities)


def _setup_from_coordinator(
    hass: HomeAssistant,
    coordinator: TapoCoordinator,
    async_add_entities: AddEntitiesCallback,
):
    if isinstance(coordinator, LightTapoCoordinator):
        model = get_short_model(coordinator.device_info.model)
        color_modes = SUPPORTED_DEVICE_AS_LIGHT.get(model)
        effects = SUPPORTED_LIGHT_EFFECTS.get(model, [])
        light = TapoLight(
            coordinator, color_modes=color_modes, supported_effects=effects
        )
        async_add_entities([light], True)


class TapoLight(BaseTapoEntity[LightTapoCoordinator], LightEntity):
    def __init__(
        self,
        coordinator: LightTapoCoordinator,
        color_modes: set[ColorMode],
        supported_effects: list[LightEffectPreset] = None,
    ):
        super().__init__(coordinator)
        self._effects = {effect.name.lower(): effect for effect in supported_effects}
        # set homeassistant light entity attributes
        self._attr_max_color_temp_kelvin = 6500
        self._attr_min_color_temp_kelvin = 2500
        self._attr_max_mireds = kelvin_to_mired(self._attr_min_color_temp_kelvin)
        self._attr_min_mireds = kelvin_to_mired(self._attr_max_color_temp_kelvin)
        self._attr_supported_features = SUPPORT_EFFECT if self._effects else 0
        self._attr_supported_color_modes = color_modes
        self._attr_effect_list = list(self._effects.keys()) if self._effects else None

    @property
    def is_on(self):
        return self.coordinator.light_state.device_on

    @property
    def brightness(self):
        current_brightness = (
            self.coordinator.light_state.lighting_effect.brightness
            if self._has_light_effect_enabled()
            else self.coordinator.light_state.brightness
        )
        return tapo_to_hass_brightness(current_brightness)

    @property
    def hs_color(self):
        hue = self.coordinator.light_state.hue
        saturation = self.coordinator.light_state.saturation
        color_temp = self.coordinator.light_state.color_temp
        if (
            color_temp is None or color_temp <= 0
        ):  # returns None if color_temp is not set
            if hue is not None and saturation is not None:
                return hue, saturation

    @property
    def color_temp(self):
        return tapo_to_hass_color_temperature(
            self.coordinator.light_state.color_temp, (self.min_mireds, self.max_mireds)
        )

    @property
    def effect(self) -> Optional[str]:
        if self._has_light_effect_enabled():
            return self.coordinator.light_state.lighting_effect.name.lower()
        else:
            return None

    def _has_light_effect_enabled(self) -> bool:
        is_enabled = (
            self._effects
            and self.coordinator.light_state.lighting_effect is not None
            and self.coordinator.light_state.lighting_effect.enable
        )
        return is_enabled

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
            return (await self.coordinator.device.off()).get_or_raise()

        (await self.coordinator.device.on()).get_or_raise()
        if effect is not None:
            (
                await self.coordinator.device.set_light_effect(
                    self._effects[effect.lower()].to_effect()
                )
            ).get_or_raise()
        elif hue_saturation is not None and ColorMode.HS in self.supported_color_modes:
            hue = int(hue_saturation[0])
            saturation = int(hue_saturation[1])
            (
                await self.coordinator.device.set_hue_saturation(hue, saturation)
            ).get_or_raise()
        elif (
            color_temp is not None
            and ColorMode.COLOR_TEMP in self.supported_color_modes
        ):
            color_temp = int(color_temp)
            (
                await self.coordinator.device.set_color_temperature(color_temp)
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
                await self.coordinator.device.set_light_effect_brightness(
                    self._effects[apply_to_effect.lower()].to_effect(), new_brightness
                )
            ).get_or_raise()
        else:
            (
                await self.coordinator.device.set_brightness(new_brightness)
            ).get_or_raise()
