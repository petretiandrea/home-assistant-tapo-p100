"""Constants for the tapo integration."""
from homeassistant.const import Platform

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "2.12.1"

SUPPORTED_HUB_DEVICE_MODEL = ["h100", "kh100", "h200"]
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
SUPPORTED_DEVICE_AS_LIGHT = [
    "l920",
    "l930",
    "l900",
    "l630",
    "l530",
    "l520",
    "l510",
    "l610",
    "tl33",
    "tl31",
    "s500d",
    "s505d",
    "s500",
    "s505",
    "ts15",
    "l535",
]
SUPPORTED_DEVICE_AS_LED_STRIP = ["l930", "l920", "l900"]

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
