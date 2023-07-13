from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from plugp100.api.tapo_client import TapoClient
from plugp100.common.functional.either import Either, Left, Right

from custom_components.tapo.const import (
    CONF_ALTERNATIVE_IP,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_POLLING_RATE_S,
    DOMAIN,
)
from custom_components.tapo.coordinators import TapoCoordinator, create_coordinator
from custom_components.tapo.utils import get_entry_data

_LOGGGER = logging.getLogger(__name__)


class DeviceNotSupported(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


async def setup_tapo_coordinator_from_dictionary(
    hass: HomeAssistant, entry: Dict[str, Any]
) -> Either[TapoCoordinator, Exception]:
    host = entry.get(CONF_HOST, None)
    return await setup_tapo_coordinator(
        hass,
        host if host is not None else entry.get(CONF_ALTERNATIVE_IP),
        entry.get(CONF_USERNAME),
        entry.get(CONF_PASSWORD),
        "",
        timedelta(seconds=entry.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)),
    )


async def setup_tapo_coordinator_from_config_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> Either[TapoCoordinator, Exception]:
    # Update our config to include new settings
    data = get_entry_data(entry)
    return await setup_tapo_coordinator(
        hass,
        data.get(CONF_HOST),
        data.get(CONF_USERNAME),
        data.get(CONF_PASSWORD),
        entry.unique_id,
        timedelta(seconds=data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)),
    )


async def setup_tapo_coordinator(
    hass: HomeAssistant,
    host: str,
    username: str,
    password: str,
    unique_id: str,
    polling_rate: timedelta,
) -> Either[TapoCoordinator, Exception]:
    client = _get_or_create_api_client(hass, username, password, unique_id)
    coordinator = await create_coordinator(hass, client, host, polling_rate)
    if coordinator is not None:
        try:
            await coordinator.async_config_entry_first_refresh()
            return Right(coordinator)
        except ConfigEntryNotReady as error:
            return Left(error)
    return Left(DeviceNotSupported(f"Device {host} not supported!"))


def _get_or_create_api_client(
    hass: HomeAssistant, username: str, password: str, unique_id: str
) -> TapoClient:
    api = (
        hass.data[DOMAIN][f"{unique_id}_api"]
        if f"{unique_id}_api" in hass.data[DOMAIN]
        else None
    )
    if api is not None:
        _LOGGGER.debug("Re-using setup API to create a coordinator")
    else:
        _LOGGGER.debug("Creating new API to create a coordinator")
        session = async_get_clientsession(hass)
        api = TapoClient(username, password, session)
    return api
