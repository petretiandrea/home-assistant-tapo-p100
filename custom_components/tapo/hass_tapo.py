import logging
from datetime import timedelta

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import PLATFORMS
from custom_components.tapo.coordinators import create_tapo_device
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDeviceCoordinator
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.hub.tapo_hub import TapoHub
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.responses.device_state import DeviceInfo as TapoDeviceInfo

from .const import TapoDevice

_LOGGER = logging.getLogger(__name__)


class HassTapo:
    def __init__(self, entry: ConfigEntry, client: TapoClient) -> None:
        self.entry = entry
        self.client = client

    async def initialize_device(self, hass: HomeAssistant) -> bool:
        polling_rate = timedelta(
            seconds=self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
        )
        host = self.entry.data.get(CONF_HOST)
        initial_state = await self._get_initial_device_state()
        model = get_short_model(initial_state.model)
        _LOGGER.info("Detected model of %s: %s", str(host), str(model))
        if tapo_device := create_tapo_device(model, self.client):
            if isinstance(tapo_device, HubDevice):
                hub = TapoHub(self.entry, tapo_device)
                return await hub.initialize_hub(hass)
            else:
                return await self._initialize_device(hass, tapo_device, polling_rate)
        else:
            raise DeviceNotSupported(f"Device {host} with mode {model} not supported!")

    async def _get_initial_device_state(self) -> TapoDeviceInfo:
        return (
            (await self.client.get_device_info())
            .map(lambda x: TapoDeviceInfo(**x))
            .get_or_raise()
        )

    async def _initialize_device(
        self, hass: HomeAssistant, device: TapoDevice, polling_rate: timedelta
    ):
        coordinator = TapoDeviceCoordinator(hass, device, polling_rate)
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
