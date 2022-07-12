"""Constants for the tapo integration."""

from homeassistant.components.light import (
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
)

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "1.2.14"

SUPPORTED_DEVICE_AS_SWITCH = ["p100", "p105", "p110", "p115"]
SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR = ["p110", "p115"]
SUPPORTED_DEVICE_AS_LIGHT = {
    "l920": SUPPORT_BRIGHTNESS | SUPPORT_COLOR,
    "l900": SUPPORT_BRIGHTNESS | SUPPORT_COLOR,
    "l530": SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP | SUPPORT_COLOR,
    "l520": SUPPORT_BRIGHTNESS,
    "l510": SUPPORT_BRIGHTNESS,
}

ISSUE_URL = "https://github.com/petretiandrea/home-assistant-tapo-p100/issues"

# list the platforms that you want to support.
PLATFORMS = ["switch", "light", "sensor", "binary_sensor"]

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
