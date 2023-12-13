from dataclasses import dataclass
from datetime import timedelta

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import PLATFORMS
from custom_components.tapo.coordinators import create_coordinator
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.hub.tapo_hub import TapoHub
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.responses.device_state import DeviceInfo

from .const import SUPPORTED_HUB_DEVICE_MODEL


@dataclass
class TapoDevice:
    entry: ConfigEntry
    client: TapoClient

    async def initialize_device(self, hass: HomeAssistant) -> bool:
        polling_rate = timedelta(
            seconds=self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        host = self.entry.data.get(CONF_HOST)
        state = (
            (await self.client.get_device_info())
            .map(lambda x: DeviceInfo(**x))
            .get_or_raise()
        )
        if get_short_model(state.model) in SUPPORTED_HUB_DEVICE_MODEL:
            hub = TapoHub(
                self.entry,
                HubDevice(self.client, subscription_polling_interval_millis=30_000),
            )
            return await hub.initialize_hub(hass)
        else:
            return await self._initialize_single_device(hass, host, polling_rate, state)

    async def _initialize_single_device(
        self,
        hass: HomeAssistant,
        host: str,
        polling_rate: timedelta,
        device_data: DeviceInfo,
    ):
        coordinator = (
            await create_coordinator(hass, self.client, host, polling_rate, device_data)
        ).get_or_raise()
        await coordinator.async_config_entry_first_refresh()  # could raise ConfigEntryNotReady
        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=coordinator,
            config_entry_update_unsub=self.entry.add_update_listener(
                _on_options_update_listener
            ),
            child_coordinators=[],
        )
        await hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)
        return True


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
