from typing import Dict, Any
from datetime import timedelta
import logging
import async_timeout
from plugp100 import TapoApiClient, TapoApiClientConfig, TapoDeviceState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.debounce import Debouncer
from custom_components.tapo.const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
)

_LOGGGER = logging.getLogger(__name__)


async def setup_tapo_coordinator_from_dictionary(
    hass: HomeAssistant, entry: Dict[str, Any]
) -> "TapoCoordinator":
    return await setup_tapo_coordinator(
        hass,
        entry.get(CONF_HOST),
        entry.get(CONF_USERNAME),
        entry.get(CONF_PASSWORD),
        "",
    )


async def setup_tapo_coordinator_from_config_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> "TapoCoordinator":
    return await setup_tapo_coordinator(
        hass,
        entry.data.get(CONF_HOST),
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        entry.unique_id,
    )


async def setup_tapo_coordinator(
    hass: HomeAssistant, host: str, username: str, password: str, unique_id: str
) -> "TapoCoordinator":
    api = (
        hass.data[DOMAIN][f"{unique_id}_api"]
        if f"{unique_id}_api" in hass.data[DOMAIN]
        else None
    )
    if api is not None:
        _LOGGGER.debug("Re-using setup API to create a coordinator")
        coordinator = TapoCoordinator(hass, client=api)
    else:
        _LOGGGER.debug("Creating new API to create a coordinator")
        session = async_get_clientsession(hass)
        config = TapoApiClientConfig(host, username, password, session)
        client = TapoApiClient.from_config(config)
        coordinator = TapoCoordinator(hass, client=client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as error:
        _LOGGGER.error("Failed to setup %s", str(error))
        raise error

    return coordinator


SCAN_INTERVAL = timedelta(seconds=30)
DEBOUNCER_COOLDOWN = 2


class TapoCoordinator(DataUpdateCoordinator[TapoDeviceState]):
    def __init__(self, hass: HomeAssistant, client: TapoApiClient):
        self.api = client
        debouncer = Debouncer(
            hass, _LOGGGER, cooldown=DEBOUNCER_COOLDOWN, immediate=True
        )
        super().__init__(
            hass,
            _LOGGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            request_refresh_debouncer=debouncer,
        )

    @property
    def tapo_client(self) -> TapoApiClient:
        return self.api

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                return await self._update_with_fallback()
        except Exception as exception:
            raise UpdateFailed(
                f"Error communication with API: {exception}"
            ) from exception

    async def _update_with_fallback(self, retry=True):
        try:
            return await self.api.get_state()
        except Exception:
            if retry:
                await self.api.login()
                return await self._update_with_fallback(False)
