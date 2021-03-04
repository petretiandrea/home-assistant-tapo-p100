"""The tapo integration."""
import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

from .tapo_helper import TapoHelper

_LOGGGER = logging.getLogger(__name__)

# list the platforms that you want to support.
# TODO: add suport for ligth and use "model" from get_state of tapo
PLATFORMS = ["switch"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""

    data = entry.as_dict()["data"]
    connector = TapoHelper(data["host"], data["username"], data["password"])

    if not await hass.async_add_executor_job(connector.setup):
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = connector

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
