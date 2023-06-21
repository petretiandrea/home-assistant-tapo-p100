from typing import Dict, Any
from datetime import timedelta
import logging
import aiohttp
import async_timeout
from plugp100 import (
    TapoApiClient,
    TapoApiClientConfig,
    TapoException,
    TapoError,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.const import CONF_SCAN_INTERVAL
from custom_components.tapo.const import (
    DEFAULT_POLLING_RATE_S,
    CONF_ALTERNATIVE_IP,
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
)

_LOGGGER = logging.getLogger(__name__)

async def setup_tapo_coordinator_from_dictionary(
    hass: HomeAssistant, entry: Dict[str, Any]
) -> "TapoCoordinator":
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
) -> "TapoCoordinator":
    return await setup_tapo_coordinator(
        hass,
        entry.data.get(CONF_HOST),
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        entry.unique_id,
        timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)),
    )


async def setup_tapo_coordinator(
    hass: HomeAssistant,
    host: str,
    username: str,
    password: str,
    unique_id: str,
    polling_rate: timedelta,
) -> "TapoCoordinator":
    api = (
        hass.data[DOMAIN][f"{unique_id}_api"]
        if f"{unique_id}_api" in hass.data[DOMAIN]
        else None
    )
    if api is not None:
        _LOGGGER.debug(
            "Re-using setup API to create a coordinator, polling rate %s",
            str(polling_rate),
        )
        coordinator = TapoCoordinator(hass, client=api, polling_interval=polling_rate)
    else:
        _LOGGGER.debug(
            "Creating new API to create a coordinator, polling rate %s",
            str(polling_rate),
        )
        session = async_get_clientsession(hass)
        config = TapoApiClientConfig(host, username, password, session)
        client = TapoApiClient.from_config(config)
        coordinator = TapoCoordinator(
            hass, client=client, polling_interval=polling_rate
        )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as error:
        _LOGGGER.exception("Failed to setup %s", str(error))
        raise error

    return coordinator


DEBOUNCER_COOLDOWN = 2


class TapoCoordinator(DataUpdateCoordinator):
    def __init__(
        self, hass: HomeAssistant, client: TapoApiClient, polling_interval: timedelta
    ):
        self.api = client
        debouncer = Debouncer(
            hass, _LOGGGER, cooldown=DEBOUNCER_COOLDOWN, immediate=True
        )
        super().__init__(
            hass,
            _LOGGGER,
            name=DOMAIN,
            update_interval=polling_interval,
            request_refresh_debouncer=debouncer,
        )
        self._include_energy = False
        self._include_power = False

    def enable_energy_monitor(self):
        self._include_energy = True
        self._include_power = True

    @property
    def tapo_client(self) -> TapoApiClient:
        return self.api

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                return await self._update_with_fallback()
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except (aiohttp.ClientError) as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception

    async def _update_with_fallback(self, retry=True):
        try:
            return await self.api.get_state(
                include_energy=self._include_energy, include_power=self._include_power
            )
        except Exception:  # pylint: disable=broad-except
            if retry:
                await self.api.login()
                return await self._update_with_fallback(False)

    def _raise_from_tapo_exception(self, exception: TapoException):
        _LOGGGER.error("Tapo exception: %s", str(exception))
        if exception.error_code == TapoError.INVALID_CREDENTIAL.value:
            raise ConfigEntryAuthFailed from exception
        else:
            raise UpdateFailed(f"Error tapo exception: {exception}") from exception
