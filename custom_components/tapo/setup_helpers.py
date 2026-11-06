import logging
from typing import Optional

import aiohttp
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.common.credentials import AuthCredential
from plugp100.devices.base import TapoDevice
from plugp100.devices.factory import DeviceConnectConfiguration, connect
from plugp100.discovery import DiscoveredDevice, connect_discovered_device

from custom_components.tapo.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

_LOGGGER = logging.getLogger(__name__)


def create_aiohttp_session(hass: HomeAssistant) -> ClientSession:
    session = async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True, quote_cookie=False)
    )
    return session


def create_device_config(config: ConfigEntry) -> DeviceConnectConfiguration:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    host, port = get_host_port(config.data.get(CONF_HOST))
    return DeviceConnectConfiguration(host=host, port=port, credentials=credential)


def get_host_port(host_user_input: str) -> (str, int):
    if ":" in host_user_input:
        parts = host_user_input.split(":", 1)
        return parts[0], int(parts[1])
    return host_user_input, 80


async def connect_with_discovery_fallback(
    discovered_device: DiscoveredDevice,
    credentials: AuthCredential,
    session: Optional[aiohttp.ClientSession] = None,
) -> TapoDevice:
    """Connect using the protocol info from discovery, falling back to protocol guessing.

    Some devices (e.g. the H110 hub) advertise an encryption scheme during
    discovery that plugp100 cannot map to a known protocol, causing
    connect_discovered_device to fail outright. Retry with protocol guessing
    in that case instead of failing the whole setup.
    """
    try:
        return await connect_discovered_device(
            discovered_device=discovered_device,
            credentials=credentials,
            session=session,
        )
    except Exception:
        _LOGGGER.warning(
            "Failed to connect to %s using discovered protocol info, "
            "falling back to protocol guessing",
            discovered_device.ip,
            exc_info=True,
        )
        if encrypt_schema := discovered_device.mgt_encrypt_schm:
            port = (
                encrypt_schema.http_port or 443
                if encrypt_schema.is_support_https
                else encrypt_schema.http_port
            )
        else:
            port = 80
        return await connect(
            config=DeviceConnectConfiguration(
                host=discovered_device.ip,
                port=port or 80,
                credentials=credentials,
                device_type=discovered_device.device_type,
            ),
            session=session,
        )
