from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from plugp100.api.tapo_client import TapoClient

from custom_components.tapo.const import (
    CONF_HOST,
    DEFAULT_POLLING_RATE_S,
    DOMAIN,
    PLATFORMS,
)
from custom_components.tapo.coordinators import HassTapoDeviceData, create_coordinator
from custom_components.tapo.errors import DeviceNotSupported


@dataclass
class TapoDevice:
    entry: ConfigEntry
    client: TapoClient

    async def initialize_device(self, hass: HomeAssistant) -> bool:
        polling_rate = timedelta(
            seconds=self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        host = self.entry.data.get(CONF_HOST)
        coordinator = await create_coordinator(hass, self.client, host, polling_rate)
        if coordinator is None:
            raise DeviceNotSupported(f"Device {host} not supported!")
        else:
            await coordinator.async_config_entry_first_refresh()  # could raise ConfigEntryNotReady
            hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
                coordinator=coordinator,
                config_entry_update_unsub=self.entry.add_update_listener(
                    _on_options_update_listener
                ),
            )
            await hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)
            return True


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
