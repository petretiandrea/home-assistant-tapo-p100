"""Constants for the tapo integration."""
from homeassistant.components.light import ColorMode
from homeassistant.const import Platform
from plugp100.api.light_effect_preset import LightEffectPreset

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "2.12.0"

SUPPORTED_HUB_DEVICE_MODEL = ["h100", "kh100", "h200"]
SUPPORTED_HUB_ALARM = "h100"
SUPPORTED_POWER_STRIP_DEVICE_MODEL = "p300"
SUPPORTED_DEVICE_AS_SWITCH = [
    "p100",
    "p105",
    "p110",
    "p115",
    "p125",
    "p125m",
    "p110m",
    "tp15",
    "p100m",
]
SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR = ["p110", "p115", "p110m", "p125m"]
SUPPORTED_DEVICE_AS_LIGHT = {
    "l920": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.HS],
    "l930": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l900": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.HS],
    "l630": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l530": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "l520": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "l510": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "l610": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "tl33": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
    "tl31": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP],
    "s500d": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "s505d": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "s500": [ColorMode.ONOFF, ColorMode.BRIGHTNESS],
    "s505": [ColorMode.ONOFF],
    "ts15": [ColorMode.ONOFF],
    "l535": [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS],
}
SUPPORTED_DEVICE_AS_LED_STRIP = ["l930", "l920", "l900"]

SUPPORTED_LIGHT_EFFECTS = {
    "l930": LightEffectPreset,
    "l920": LightEffectPreset,
    "l900": LightEffectPreset,
}

ISSUE_URL = "https://github.com/petretiandrea/home-assistant-tapo-p100/issues"

# list the platforms that you want to support.
PLATFORMS = [Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.LIGHT]

HUB_PLATFORMS = [
    Platform.SIREN,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.NUMBER,
]

CONF_HOST = "host"
CONF_MAC = "mac"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ADVANCED_SETTINGS = "advanced_settings"
CONF_TRACK_DEVICE = "track_device_mac"

CONF_DEVICE_TYPE = "device_type"

STEP_INIT = "user"
STEP_ADVANCED_SETTINGS = "advanced_config"

DEFAULT_POLLING_RATE_S = 30  # 30 seconds

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
