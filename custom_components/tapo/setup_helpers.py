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
    session: Optional[ClientSession] = None,
) -> TapoDevice:
    """Connect using the discovered protocol info, guessing if it does not work.

    The encryption scheme recorded at discovery is not always usable later.
    It can fail in two different places:

    - `connect_discovered_device` raises, because plugp100 cannot build a
      protocol for the advertised scheme;
    - the connection is built, but the device no longer answers that protocol.
      A firmware update can withdraw one: P115 firmware 1.4.8 stopped offering
      TPAP, and entries paired while it was offered keep asking for it.

    Only an exchange tells the two apart, because the handshake is deferred to
    the first request, so the connection is probed here before it is returned.
    Guessing is what an entry added by hand does anyway, which is why plugs
    added by hand kept working while discovered ones did not.
    """
    try:
        device = await connect_discovered_device(
            discovered_device=discovered_device,
            credentials=credentials,
            session=session,
        )
        (await device.client.get_device_info()).get_or_raise()
        return device
    except Exception:
        _LOGGGER.warning(
            "Discovered protocol info for %s is unusable, guessing the protocol",
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
        port = None

    return await connect(
        config=DeviceConnectConfiguration(
            host=discovered_device.ip,
            port=port or 80,
            credentials=credentials,
            device_type=discovered_device.device_type,
        ),
        session=session,
    )
