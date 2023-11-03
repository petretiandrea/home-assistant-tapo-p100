"""The tapo integration."""
import asyncio
import logging
from typing import cast
from typing import Optional

from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.hub.tapo_hub import TapoHub
from custom_components.tapo.migrations import migrate_entry_to_v6
from custom_components.tapo.setup_helpers import setup_tapo_api
from custom_components.tapo.tapo_device import TapoDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from plugp100.api.hub.hub_device import HubDevice
from plugp100.responses.device_state import DeviceInfo

from .const import DOMAIN
from .const import HUB_PLATFORMS
from .const import PLATFORMS
from .const import SUPPORTED_HUB_DEVICE_MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        api = await setup_tapo_api(hass, entry)
        state = (
            (await api.get_device_info()).map(lambda x: DeviceInfo(**x)).get_or_raise()
        )
        if get_short_model(state.model) in SUPPORTED_HUB_DEVICE_MODEL:
            hub = TapoHub(
                entry,
                HubDevice(api, subscription_polling_interval_millis=30_000),
            )
            return await hub.initialize_hub(hass)
        else:
            device = TapoDevice(entry, api)
            return await device.initialize_device(hass)
    except DeviceNotSupported as error:
        raise error
    except Exception as error:
        raise ConfigEntryNotReady from error


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version != 6:
        await migrate_entry_to_v6(hass, config_entry)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    platform_to_unload = (
        PLATFORMS if not entry.data.get("is_hub", False) else HUB_PLATFORMS
    )
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in platform_to_unload
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
