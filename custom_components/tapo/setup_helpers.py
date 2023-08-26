import logging
from datetime import timedelta
from typing import Any
from typing import Dict

from custom_components.tapo.const import CONF_ALTERNATIVE_IP
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import create_coordinator
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.tapo_device import TapoDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential

_LOGGGER = logging.getLogger(__name__)


async def setup_tapo_hub(hass: HomeAssistant, config: ConfigEntry) -> HubDevice:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    api = await connect_tapo_client(
        hass,
        credential,
        config.data.get(CONF_HOST),
        config.unique_id,
    )
    hub = HubDevice(api)
    return hub


async def setup_tapo_device(hass: HomeAssistant, config: ConfigEntry) -> TapoDevice:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    api = await connect_tapo_client(
        hass,
        credential,
        config.data.get(CONF_HOST),
        config.unique_id,
    )
    return TapoDevice(config, api)


async def setup_from_platform_config(
    hass: HomeAssistant, config: Dict[str, Any]
) -> TapoCoordinator:
    host = config.get(CONF_HOST, None)
    polling_rate = timedelta(
        seconds=config.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
    )
    credential = AuthCredential(config.get(CONF_USERNAME), config.get(CONF_PASSWORD))
    ip_address = host if host is not None else config.get(CONF_ALTERNATIVE_IP)
    client = await connect_tapo_client(hass, credential, ip_address, "")
    return await create_coordinator(
        hass,
        client,
        ip_address,
        polling_rate,
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
        _LOGGGER.debug(f"Creating new API to create a coordinator for {unique_id}")
        session = async_get_clientsession(hass)
        api = await TapoClient.connect(credentials, ip_address, session)
    return api
