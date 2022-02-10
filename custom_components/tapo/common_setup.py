import async_timeout
import logging
from typing import Dict, Any
from datetime import timedelta
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from plugp100 import TapoApiClient, TapoDeviceState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from custom_components.tapo.const import (
    DOMAIN,
    PLATFORMS,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
)


_LOGGGER = logging.getLogger(__name__)


async def setup_tapo_coordinator_from_dictionary(
    hass: HomeAssistant, entry: Dict[str, Any]
) -> "TapoUpdateCoordinator":
    return await setup_tapo_coordinator(
        hass,
        entry.get(CONF_HOST),
        entry.get(CONF_USERNAME),
        entry.get(CONF_PASSWORD),
    )


async def setup_tapo_coordinator_from_config_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> "TapoUpdateCoordinator":
    return await setup_tapo_coordinator(
        hass,
        entry.data.get(CONF_HOST),
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
    )


async def setup_tapo_coordinator(
    hass: HomeAssistant, host: str, username: str, password: str
) -> "TapoUpdateCoordinator":
    session = async_get_clientsession(hass)
    client = TapoApiClient(host, username, password, session)

    coordinator = TapoUpdateCoordinator(hass, client=client)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise Exception("Failed to retrieve first tapo data")

    return coordinator


SCAN_INTERVAL = timedelta(seconds=30)
DEBOUNCER_COOLDOWN = 2


class TapoUpdateCoordinator(DataUpdateCoordinator[TapoDeviceState]):
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
            raise UpdateFailed() from exception

    async def _update_with_fallback(self, retry=True):
        try:
            return await self.api.get_state()
        except Exception as error:
            if retry:
                await self.api.login()
                return await self._update_with_fallback(False)
