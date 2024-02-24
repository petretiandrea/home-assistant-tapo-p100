import logging
from typing import Any
from typing import Dict

from custom_components.tapo.const import CONF_ALTERNATIVE_IP
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_MAC
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.helpers import find_adapter_for
from custom_components.tapo.helpers import get_network_of
from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential
from plugp100.discovery.arp_lookup import ArpLookup

_LOGGGER = logging.getLogger(__name__)


async def create_api_from_config(
    hass: HomeAssistant, config: ConfigEntry
) -> TapoClient:
    address_finder = TapoAddressFinder(hass, config)
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    address = await address_finder.lookup()
    _LOGGGER.debug(
        "Creating new API to create a coordinator for %s to address %s",
        config.unique_id,
        address,
    )
    session = async_create_clientsession(hass)
    host, port = get_host_port(address)
    return TapoClient.create(credential, address=host, port=port, http_session=session)


async def setup_from_platform_config(
    hass: HomeAssistant, config: Dict[str, Any]
) -> TapoClient:
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
        minor_version=1,
    )
    return await create_api_from_config(hass, temporary_entry)


class TapoAddressFinder:
    def __init__(self, hass: HomeAssistant, config: ConfigEntry):
        self._hass = hass
        self._config = config

    async def lookup(self) -> str:
        if (
            self._config.data.get(CONF_TRACK_DEVICE, False)
            and self._config.data.get(CONF_MAC, None) is not None
        ):
            if self._config.data.get(CONF_MAC, None) is not None:
                return await try_track_ip_address(
                    self._hass,
                    self._config.data.get(CONF_MAC),
                    self._config.data.get(CONF_HOST),
                )
            else:
                logging.warning(
                    "Tracking mac address enabled, but no MAC address found on config entry"
                )
                return self._config.data.get(CONF_HOST)
        else:
            return self._config.data.get(CONF_HOST)


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
            device_ip = await ArpLookup.lookup(
                mac.replace("-", ":"), target_network, timeout=5
            )
            return device_ip.get_or_else(last_known_ip)
        else:
            _LOGGGER.warning(
                "No adapter found for %s with last ip %s", mac, last_known_ip
            )
    except PermissionError:
        _LOGGGER.warning("No permission to scan network")

    return last_known_ip


# async def setup_from_platform_config(
#     hass: HomeAssistant, config: Dict[str, Any]
# ) -> TapoCoordinator:
#     temporary_entry = ConfigEntry(
#         version=1,
#         domain="",
#         title="",
#         source="config_yaml",
#         data={
#             CONF_HOST: config.get(CONF_HOST, config.get(CONF_ALTERNATIVE_IP, None)),
#             CONF_USERNAME: config.get(CONF_USERNAME),
#             CONF_PASSWORD: config.get(CONF_PASSWORD),
#         },
#         options={CONF_TRACK_DEVICE: config.get(CONF_TRACK_DEVICE, False)},
#     )
#     client = await create_api_from_config(hass, temporary_entry)
#     state = (
#         (await client.get_device_info())
#         .map(lambda x: TapoDeviceInfo(**x))
#         .get_or_raise()
#     )
#     return await create_coordinator(
#         hass,
#         client,
#         temporary_entry.data.get(CONF_HOST),
#         polling_interval=timedelta(
#             seconds=config.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
#         ),
#         device_info=state,
#     )


def get_host_port(host_user_input: str) -> (str, int):
    if ":" in host_user_input:
        parts = host_user_input.split(":", 1)
        return (parts[0], int(parts[1]))
    return (host_user_input, 80)
