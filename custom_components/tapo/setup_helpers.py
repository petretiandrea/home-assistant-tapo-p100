import logging
from datetime import timedelta
from typing import Any
from typing import Dict

from custom_components.tapo.const import CONF_ALTERNATIVE_IP
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_MAC
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import create_coordinator
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.helpers import find_adapter_for
from custom_components.tapo.helpers import get_network_of
from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential
from plugp100.discovery.local_device_finder import LocalDeviceFinder

_LOGGGER = logging.getLogger(__name__)


async def setup_tapo_api(hass: HomeAssistant, config: ConfigEntry) -> TapoClient:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    if (
        config.data.get(CONF_TRACK_DEVICE, False)
        and config.data.get(CONF_MAC, None) is not None
    ):
        if config.data.get(CONF_MAC, None) is not None:
            address = await try_track_ip_address(
                hass, config.data.get(CONF_MAC), config.data.get(CONF_HOST)
            )
        else:
            logging.warning(
                "Tracking mac address enabled, but no MAC address found on config entry"
            )
            address = config.data.get(CONF_HOST)
    else:
        address = config.data.get(CONF_HOST)

    return await connect_tapo_client(
        hass,
        credential,
        address,
        config.unique_id,
    )


async def setup_from_platform_config(
    hass: HomeAssistant, config: Dict[str, Any]
) -> TapoCoordinator:
    temporary_entry = ConfigEntry(
        version=1,
        domain="",
        title="",
        source="config_yaml",
        data={
            CONF_HOST: config.get(CONF_HOST, config.get(CONF_ALTERNATIVE_IP, None)),
            CONF_USERNAME: config.get(CONF_USERNAME),
            CONF_PASSWORD: config.get(CONF_PASSWORD),
        },
        options={CONF_TRACK_DEVICE: config.get(CONF_TRACK_DEVICE, False)},
    )
    client = await setup_tapo_api(hass, temporary_entry)
    return await create_coordinator(
        hass,
        client,
        temporary_entry.data.get(CONF_HOST),
        polling_interval=timedelta(
            seconds=config.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        ),
    )


async def connect_tapo_client(
    hass: HomeAssistant, credentials: AuthCredential, ip_address: str, unique_id: str
) -> TapoClient:
    api = (
        hass.data[DOMAIN][f"{unique_id}_api"]
        if f"{unique_id}_api" in hass.data[DOMAIN]
        else None
    )
    if api is not None:
        _LOGGGER.debug("Re-using setup API to create a coordinator")
    else:
        _LOGGGER.debug("Creating new API to create a coordinator for %s", unique_id)
        session = async_create_clientsession(hass)
        host, port = get_host_port(ip_address)
        api = TapoClient.create(
            credentials, address=host, port=port, http_session=session
        )
        await api.initialize()
    return api


async def try_track_ip_address(
    hass: HomeAssistant, mac: str, last_known_ip: str
) -> str:
    _LOGGGER.info(
        "Trying to track ip address of %s, last known ip is %s", mac, last_known_ip
    )
    adapters = await network.async_get_adapters(hass)
    adapter = await find_adapter_for(adapters, last_known_ip)
    try:
        if adapter is not None:
            target_network = get_network_of(adapter)
            device = await LocalDeviceFinder.scan_one(
                mac.replace("-", ":"), target_network, timeout=5
            )
            return device.get_or_else(last_known_ip)
        else:
            _LOGGGER.warning(
                "No adapter found for %s with last ip %s", mac, last_known_ip
            )
    except PermissionError:
        _LOGGGER.warning("No permission to scan network")

    return last_known_ip


def get_host_port(host_user_input: str) -> (str, int):
    if ":" in host_user_input:
        parts = host_user_input.split(":", 1)
        return (parts[0], int(parts[1]))
    return (host_user_input, 80)
