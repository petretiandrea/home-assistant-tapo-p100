"""The tapo integration."""
import asyncio
from dataclasses import dataclass
import logging
from typing import Optional, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.tapo.coordinators import HassTapoDeviceData, TapoCoordinator
from custom_components.tapo.helpers import value_or_raise
from custom_components.tapo.hub.tapo_hub import TapoHub
from custom_components.tapo.setup_helpers import (
    DeviceNotSupported,
    setup_tapo_coordinator_from_config_entry,
    setup_tapo_hub,
)

from .const import DEFAULT_POLLING_RATE_S, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        if entry.data.get("is_hub", False):
            hub = TapoHub(entry, setup_tapo_hub(hass, entry))
            return await hub.initialize_hub(hass)
        else:
            coordinator = value_or_raise(
                await setup_tapo_coordinator_from_config_entry(hass, entry)
            )
            hass.data[DOMAIN][entry.entry_id] = HassTapoDeviceData(
                coordinator=coordinator,
                config_entry_update_unsub=entry.add_update_listener(
                    on_options_update_listener
                ),
            )
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
    except DeviceNotSupported as error:
        raise error
    except Exception as error:
        raise ConfigEntryNotReady from error


async def on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


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
        data = cast(
            Optional[HassTapoDeviceData], hass.data[DOMAIN].pop(entry.entry_id, None)
        )
        if data:
            data.config_entry_update_unsub()

    return unload_ok
