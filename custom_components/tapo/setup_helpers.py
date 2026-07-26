import logging
from typing import Optional

import aiohttp
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.common.credentials import AuthCredential
from plugp100.devices.factory import DeviceConnectConfiguration, TapoDevice, connect
from plugp100.discovery import DiscoveredDevice

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


_SUPPORTED_ENCRYPTION_TYPES = {"klap", "aes"}


async def _connect_tpap_device(
    discovered: DiscoveredDevice,
    credential: AuthCredential,
    session: Optional[ClientSession] = None,
) -> TapoDevice:
    """Connect to a TPAP device using our custom TpapProtocol implementation."""
    from custom_components.tapo.protocols.tpap_protocol import TpapProtocol
    from plugp100.api.tapo_client import TapoClient
    from plugp100.devices.bulb import TapoBulb
    from plugp100.devices.plug import TapoPlug

    encrypt_schema = discovered.mgt_encrypt_schm
    initial_tls = None
    initial_port = None
    initial_mac = discovered.mac or ""

    if encrypt_schema:
        initial_port = encrypt_schema.http_port
        initial_tls = 2 if encrypt_schema.is_support_https else 0

    host = discovered.ip
    port = initial_port or 80
    url = f"http://{host}:{port}"
    protocol = TpapProtocol(
        auth_credential=credential,
        url=url,
        http_session=session,
        initial_tpap_port=initial_port,
        initial_tpap_tls=initial_tls,
        initial_device_mac=initial_mac,
    )
    client = TapoClient(
        auth_credential=credential,
        url=url,
        protocol=protocol,
        http_session=session,
    )

    device_type = (discovered.device_type or "").upper()
    if device_type == "SMART.TAPOBULB":
        device = TapoBulb(host, port, client)
    elif device_type == "SMART.TAPOPLUG":
        device = TapoPlug(host, port, client)
    else:
        from plugp100.devices.base import TapoDevice
        device = TapoDevice(host, port, client)

    try:
        await device.update()
    except Exception as e:
        await protocol.close()
        raise
    return device


async def connect_discovered_device_with_fallback(
    discovered: DiscoveredDevice,
    credential: AuthCredential,
    session: Optional[ClientSession] = None,
) -> TapoDevice:
    """Connect to a discovered Tapo device, routing to the appropriate protocol based on encryption type."""
    encryption_type = None
    if encrypt_schema := discovered.mgt_encrypt_schm:
        encryption_type = encrypt_schema.encrypt_type

    if encryption_type and encryption_type.lower() == "tpap":
        _LOGGGER.info(
            "Discovered device %s reports TPAP encryption, using TPAP protocol",
            discovered.ip,
        )
        return await _connect_tpap_device(discovered, credential, session)

    if encryption_type and encryption_type.lower() not in _SUPPORTED_ENCRYPTION_TYPES:
        _LOGGGER.warning(
            "Discovered device %s reports unsupported encryption type '%s', falling back to protocol guessing",
            discovered.ip,
            encryption_type,
        )
        port = (
            encrypt_schema.http_port or 443
            if encrypt_schema.is_support_https
            else encrypt_schema.http_port
            if encrypt_schema
            else 80
        )
        config = DeviceConnectConfiguration(
            host=discovered.ip,
            port=port,
            credentials=credential,
            device_type=discovered.device_type,
            encryption_type=None,
        )
        return await connect(config, session)
    else:
        from plugp100.discovery import connect_discovered_device

        return await connect_discovered_device(discovered, credential, session)
