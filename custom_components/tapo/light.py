import logging
from typing import Any, Dict, Optional, Union, cast

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    SUPPORT_EFFECT,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
    color_temperature_mired_to_kelvin as mired_to_kelvin,
)
from plugp100.api.light_effect_preset import LightEffectPreset
from plugp100.responses.device_state import LedStripDeviceState, LightDeviceState

from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_LIGHT,
    SUPPORTED_LIGHT_EFFECTS,
)
from custom_components.tapo.coordinators import (
    HassTapoDeviceData,
    LightTapoCoordinator,
    TapoCoordinator,
)
from custom_components.tapo.entity import BaseTapoEntity
from custom_components.tapo.helpers import clamp, get_short_model, value_or_raise
from custom_components.tapo.setup_helpers import setup_from_platform_config

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
        model = get_short_model(coordinator.get_device_info().model)
        color_modes = SUPPORTED_DEVICE_AS_LIGHT.get(model)
        effects = SUPPORTED_LIGHT_EFFECTS.get(model, [])
        light = TapoLight(
            coordinator, color_modes=color_modes, supported_effects=effects
        )
        async_add_entities([light], True)


class TapoLight(
    BaseTapoEntity[Union[LightDeviceState, LedStripDeviceState]], LightEntity
):
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
        return self.coordinator.data.device_on

    @property
    def brightness(self):
        if self._effects and self.coordinator.data.lighting_effect is not None:
            return round((self.coordinator.data.lighting_effect.brightness * 255) / 100)
        else:
            return round((self.coordinator.data.brightness * 255) / 100)

    @property
    def hs_color(self):
        hue = self.coordinator.data.hue
        saturation = self.coordinator.data.saturation
        color_temp = self.coordinator.data.color_temp
        if (
            color_temp is None or color_temp <= 0
        ):  ## returns None if color_temp is not set
            if hue is not None and saturation is not None:
                return hue, saturation

    @property
    def color_temp(self):
        color_temp = self.coordinator.data.color_temp
        if color_temp is not None and color_temp > 0:
            return clamp(
                kelvin_to_mired(color_temp),
                min_value=self.min_mireds,
                max_value=self.max_mireds,
            )
        else:
            return None

    @property
    def effect(self) -> Optional[str]:
        if (
            self._effects
            and self.coordinator.data.lighting_effect is not None
            and self.coordinator.data.lighting_effect.enable
        ):
            return self.coordinator.data.lighting_effect.name.lower()
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

        if (
            brightness is not None
            or color is not None
            or color_temp is not None
            or effect is not None
        ):
            if self.is_on is False:
                value_or_raise(
                    await self.coordinator.device.on()
                )  # execute with fallback?
            if color is not None and ColorMode.HS in self.supported_color_modes:
                hue = int(color[0])
                saturation = int(color[1])
                await self._change_color(hue, saturation)
            elif (
                color_temp is not None
                and ColorMode.COLOR_TEMP in self.supported_color_modes
            ):
                color_temp = int(color_temp)
                await self._change_color_temp(color_temp)
            if brightness is not None:
                await self._change_brightness(brightness)
            if effect is not None:
                value_or_raise(
                    await self.coordinator.device.set_light_effect(
                        self._effects[effect].to_effect()
                    )
                )
        else:
            value_or_raise(await self.coordinator.device.on())

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        value_or_raise(await self.coordinator.device.off())
        await self.coordinator.async_request_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = round((new_brightness / 255) * 100)
        _LOGGER.debug("Change brightness to: %s", str(brightness_to_set))
        if self.effect is not None:
            value_or_raise(
                await self.coordinator.device.set_light_effect_brightness(
                    self._effects[self.effect].to_effect(), brightness_to_set
                )
            )
        else:
            value_or_raise(
                await self.coordinator.device.set_brightness(brightness_to_set)
            )

    async def _change_color_temp(self, color_temp):
        _LOGGER.debug("Change color temp to: %s", str(color_temp))
        constraint_color_temp = clamp(color_temp, self.min_mireds, self.max_mireds)
        kelvin_color_temp = clamp(
            mired_to_kelvin(constraint_color_temp),
            min_value=self.min_color_temp_kelvin,
            max_value=self.max_color_temp_kelvin,
        )

        value_or_raise(
            await self.coordinator.device.set_color_temperature(kelvin_color_temp)
        )

    async def _change_color(self, hue, saturation):
        _LOGGER.debug("Change colors to: (%s, %s)", str(hue), str(saturation))
        value_or_raise(
            await self.coordinator.device.set_hue_saturation(hue, saturation)
        )
