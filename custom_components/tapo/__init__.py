"""The tapo integration."""
import asyncio
from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.tapo.common_setup import (
    DeviceNotSupported,
    setup_tapo_coordinator_from_config_entry,
)
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.utils import value_or_raise

from .const import DEFAULT_POLLING_RATE_S, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


@dataclass
class HassTapoDeviceData:
    coordinator: TapoCoordinator


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""
    try:
        coordinator = value_or_raise(
            await setup_tapo_coordinator_from_config_entry(hass, entry)
        )
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = HassTapoDeviceData(coordinator=coordinator)
        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )
        return True
    except DeviceNotSupported as error:
        raise error
    except Exception as error:
        raise ConfigEntryNotReady from error


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new = {**config_entry.data, CONF_SCAN_INTERVAL: DEFAULT_POLLING_RATE_S}

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

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
        _LOGGER.info("Unloaded entry for %s", str(entry.entry_id))
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
