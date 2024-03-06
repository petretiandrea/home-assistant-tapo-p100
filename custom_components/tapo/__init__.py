"""The tapo integration."""
import asyncio
import logging
from typing import Any
from typing import cast
from typing import Optional

from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.discovery import discovery_tapo_devices
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.hass_tapo import HassTapo
from custom_components.tapo.migrations import migrate_entry_to_v8
from custom_components.tapo.setup_helpers import create_api_from_config
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.event import async_track_time_interval
from plugp100.discovery.discovered_device import DiscoveredDevice

from .const import CONF_DISCOVERED_DEVICE_INFO
from .const import CONF_HOST
from .const import CONF_MAC
from .const import DEFAULT_POLLING_RATE_S
from .const import DISCOVERY_FEATURE_FLAG
from .const import DISCOVERY_INTERVAL
from .const import DOMAIN
from .const import HUB_PLATFORMS
from .const import PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    domain_config = config.get(DOMAIN, {})
    discovery_enabled = domain_config.get(DISCOVERY_FEATURE_FLAG, True)
    if discovery_enabled:

        async def _start_discovery(_: Any = None) -> None:
            if device_found := await discovery_tapo_devices(hass):
                async_create_discovery_flow(hass, device_found)

        hass.async_create_background_task(_start_discovery(), "Initial tapo discovery")
        async_track_time_interval(
            hass, _start_discovery, DISCOVERY_INTERVAL, cancel_on_shutdown=True
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        api = await create_api_from_config(hass, entry)
        device = HassTapo(entry, api)
        return await device.initialize_device(hass)
    except DeviceNotSupported as error:
        raise error
    except Exception as error:
        raise ConfigEntryNotReady from error


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version != 8:
        await migrate_entry_to_v8(hass, config_entry)
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


def async_create_discovery_flow(
    hass: HomeAssistant,
    discovered_devices: dict[str, DiscoveredDevice],
) -> None:
    for mac, device in discovered_devices.items():
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={
                "source": config_entries.SOURCE_INTEGRATION_DISCOVERY,
                CONF_DISCOVERED_DEVICE_INFO: device,
            },
            data={
                CONF_HOST: device.ip,
                CONF_MAC: dr.format_mac(mac),
                CONF_SCAN_INTERVAL: DEFAULT_POLLING_RATE_S,
            },
        )
