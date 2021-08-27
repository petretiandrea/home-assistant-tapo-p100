"""The tapo integration."""
from dataclasses import dataclass
import logging
import asyncio
import async_timeout
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from voluptuous.validators import Any

from .const import DOMAIN, PLATFORMS, CONF_HOST, CONF_USERNAME, CONF_PASSWORD

from plugp100 import TapoApiClient, TapoDeviceState

_LOGGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""

    host = entry.data.get(CONF_HOST)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    session = async_get_clientsession(hass)
    client = TapoApiClient(host, username, password, session)

    coordinator = TapoUpdateCoordinator(hass, client=client)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


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
