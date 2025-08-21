"""Constants for the tapo integration."""
from datetime import timedelta
from enum import Enum
from typing import Union

from homeassistant.const import Platform

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "3.1.2"

DISCOVERY_FEATURE_FLAG = "discovery"
DISCOVERY_INTERVAL = timedelta(minutes=10)
DISCOVERY_TIMEOUT = 5

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