import logging

import aiohttp
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.common.credentials import AuthCredential
from plugp100.new.device_factory import DeviceConnectConfiguration

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME

_LOGGGER = logging.getLogger(__name__)


def create_aiohttp_session(hass: HomeAssistant) -> ClientSession:
    session = async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar(unsafe=True, quote_cookie=False))
    return session


def create_device_config(config: ConfigEntry) -> DeviceConnectConfiguration:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    host, port = get_host_port(config.data.get(CONF_HOST))
    return DeviceConnectConfiguration(
        host=host,
        port=port,
        credentials=credential
    )


def get_host_port(host_user_input: str) -> (str, int):
    if ":" in host_user_input:
        parts = host_user_input.split(":", 1)
        return parts[0], int(parts[1])
    return host_user_input, 80
