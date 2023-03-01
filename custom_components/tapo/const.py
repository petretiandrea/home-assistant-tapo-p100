"""Constants for the tapo integration."""

from homeassistant.components.light import ColorMode
from plugp100 import LightEffectPreset

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "1.6.1"

SUPPORTED_DEVICE_AS_SWITCH = ["p100", "p105", "p110", "p115", "p125"]
SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR = ["p110", "p115"]
SUPPORTED_DEVICE_AS_LIGHT = {
    "l920": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.HS],
    "l930": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l900": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.HS],
    "l630": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l530": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l520": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "l510": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "l610": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
}

SUPPORTED_LIGHT_EFFECTS = {
    "l930": lambda: [
        LightEffectPreset.aurora(),
        LightEffectPreset.bubbling_calderon(),
        LightEffectPreset.christmas(),
        LightEffectPreset.candy_cane(),
        LightEffectPreset.flicker(),
        LightEffectPreset.christmas_light(),
        LightEffectPreset.hanukkah(),
        LightEffectPreset.haunted_mansion(),
        LightEffectPreset.icicle(),
        LightEffectPreset.lightning(),
        LightEffectPreset.ocean(),
        LightEffectPreset.rainbow(),
        LightEffectPreset.raindrop(),
        LightEffectPreset.spring(),
        LightEffectPreset.sunrise(),
        LightEffectPreset.sunset(),
        LightEffectPreset.valentines(),
    ],
    "l920": lambda: [
        LightEffectPreset.aurora(),
        LightEffectPreset.bubbling_calderon(),
        LightEffectPreset.christmas(),
        LightEffectPreset.candy_cane(),
        LightEffectPreset.flicker(),
        LightEffectPreset.christmas_light(),
        LightEffectPreset.hanukkah(),
        LightEffectPreset.haunted_mansion(),
        LightEffectPreset.icicle(),
        LightEffectPreset.lightning(),
        LightEffectPreset.ocean(),
        LightEffectPreset.rainbow(),
        LightEffectPreset.raindrop(),
        LightEffectPreset.spring(),
        LightEffectPreset.sunrise(),
        LightEffectPreset.sunset(),
        LightEffectPreset.valentines(),
    ],
    "l900": lambda: [
        LightEffectPreset.aurora(),
        LightEffectPreset.bubbling_calderon(),
        LightEffectPreset.christmas(),
        LightEffectPreset.candy_cane(),
        LightEffectPreset.flicker(),
        LightEffectPreset.christmas_light(),
        LightEffectPreset.hanukkah(),
        LightEffectPreset.haunted_mansion(),
        LightEffectPreset.icicle(),
        LightEffectPreset.lightning(),
        LightEffectPreset.ocean(),
        LightEffectPreset.rainbow(),
        LightEffectPreset.raindrop(),
        LightEffectPreset.spring(),
        LightEffectPreset.sunrise(),
        LightEffectPreset.sunset(),
        LightEffectPreset.valentines(),
    ],
}

ISSUE_URL = "https://github.com/petretiandrea/home-assistant-tapo-p100/issues"

# list the platforms that you want to support.
PLATFORMS = ["switch", "light", "sensor", "binary_sensor"]

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CONF_ALTERNATIVE_IP = "ip_address"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
