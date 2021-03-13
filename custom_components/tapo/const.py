"""Constants for the tapo integration."""

NAME = "tapo"
DOMAIN = "tapo"
VERSION = "1.0"

SUPPORTED_DEVICE_AS_SWITCH = ["p100", "p105"]
SUPPORTED_DEVICE_AS_LIGHT = ["l530 series"]  # TODO: change this

ISSUE_URL = "https://github.com/petretiandrea/home-assistant-tapo-p100/issues"

# list the platforms that you want to support.
# TODO: add suport for ligth and use "model" from get_state of tapo
PLATFORMS = ["switch", "light"]

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
