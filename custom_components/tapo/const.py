"""Constants for the tapo integration."""
from datetime import timedelta
from enum import Enum
from typing import Union

from homeassistant.const import Platform

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "3.0.0"

DISCOVERY_FEATURE_FLAG = "discovery"
DISCOVERY_INTERVAL = timedelta(minutes=10)
DISCOVERY_TIMEOUT = 5

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
    "l535e",
    "l535b",
    "tl135",
    "tl135e",
]
SUPPORTED_DEVICE_AS_LED_STRIP = ["l930", "l920", "l900"]


SUPPORTED_DEVICES = (
    SUPPORTED_DEVICE_AS_LED_STRIP
    + SUPPORTED_DEVICE_AS_LIGHT
    + SUPPORTED_HUB_DEVICE_MODEL
    + SUPPORTED_DEVICE_AS_SWITCH
    + [SUPPORTED_POWER_STRIP_DEVICE_MODEL]
)

ISSUE_URL = "https://github.com/petretiandrea/home-assistant-tapo-p100/issues"

# list the platforms that you want to support.
PLATFORMS = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.SIREN,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.UPDATE,
]


CONF_HOST = "host"
CONF_MAC = "mac"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ADVANCED_SETTINGS = "advanced_settings"

CONF_DISCOVERED_DEVICE_INFO = "discovered_device_info"

STEP_INIT = "user"
STEP_ADVANCED_SETTINGS = "advanced_config"
STEP_DISCOVERY_REQUIRE_AUTH = "discovery_auth_confirm"

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