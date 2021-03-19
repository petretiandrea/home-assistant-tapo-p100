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
        self._max_merids = kelvin_to_mired(2500)
        self._min_merids = kelvin_to_mired(6500)
        self.emulated = Emulated()

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
        pass
        # hue = self._tapo_coordinator.data.hue
        # saturation = self._tapo_coordinator.data.saturation
        # if hue and saturation:
        #    return hue, saturation

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
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._change_brightness(kwargs.get(ATTR_BRIGHTNESS, 255))

        if kwargs.get(ATTR_HS_COLOR) and self.supported_features & SUPPORT_COLOR:
            hue = int(kwargs.get(ATTR_HS_COLOR)[0])
            saturation = int(kwargs.get(ATTR_HS_COLOR)[1])
            await self._change_color([hue, saturation])
        elif (
            kwargs.get(ATTR_COLOR_TEMP) and self.supported_features & SUPPORT_COLOR_TEMP
        ):
            color_temp = int(kwargs.get(ATTR_COLOR_TEMP))
            await self._change_color_temp(color_temp)

        await self._tapo_coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_refresh()

    async def _change_brightness(self, new_brightness):
        brightness_to_set = (new_brightness / 255) * 100

        async def _set_brightness():
            await self._tapo_coordinator.api.set_brightness(brightness_to_set)

        await self._execute_with_fallback(_set_brightness)

    async def _change_color_temp(self, color_temp):
        constraint_color_temp = max(self._min_merids, min(color_temp, self._max_merids))
        kelvin_color_temp = mired_to_kelvin(constraint_color_temp)
        await self._execute_with_fallback(
            lambda: self._tapo_coordinator.api.set_color_temperature(kelvin_color_temp)
        )

    async def _change_color(self, hs_color):
        hue = hs_color[0] / 360 * 65536
        saturation = hs_color[1] / 100 * 255
        await self._execute_with_fallback(
            self._tapo_coordinator.api.set_hue_saturation(hue, saturation)
        )


EX = {
    "device_id": "80235BB614053ACC4A9E499A85827FC91D7955EE",
    "fw_ver": "1.1.9 Build 20210122 Rel. 56165",
    "hw_ver": "1.0.0",
    "type": "SMART.TAPOBULB",
    "model": "L530 Series",
    "mac": "60-32-B1-FD-3E-17",
    "hw_id": "93F94D88DA9499F43B929DD38EBDF09A",
    "fw_id": "7BECA9DC454565672FEC87D1104F9972",
    "oem_id": "D042998E924F77C9E23A75966003ADD8",
    "specs": "EU",
    "lang": "en_US",
    "device_on": True,
    "on_time": 2712,
    "overheated": False,
    "nickname": "VGFwbyA1MzBlIEJlZHJvb20=",
    "avatar": "hang_lamp_1",
    "brightness": 100,
    "dynamic_light_effect_enable": False,
    "color_temp": 2500,
    "default_states": {
        "type": "last_states",
        "state": {"brightness": 100, "color_temp": 2500},
    },
    "time_diff": 60,
    "has_set_location_info": True,
    "ip": "removed",
    "ssid": "removed",
    "signal_level": 2,
    "rssi": -60,
}


class Emulated:
    def __init__(self):
        self.state = EX

    def set_brightness(self, value):
        self.state["brightness"] = value

    def set_color_temp(self, color_temp):
        self.state["color_temp"] = color_temp

    def get_state(self) -> TapoDeviceState:
        return TapoDeviceState(self.state)