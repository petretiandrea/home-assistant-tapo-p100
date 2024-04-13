import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from plugp100.discovery import DiscoveredDevice
from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from plugp100.new.tapodevice import TapoDevice

from custom_components.tapo.const import DEFAULT_POLLING_RATE_S, CONF_DISCOVERED_DEVICE_INFO
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import PLATFORMS
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.hass_tapo_hub import TapoHub, HassTapoHub
from custom_components.tapo.setup_helpers import create_aiohttp_session

_LOGGER = logging.getLogger(__name__)


class HassTapo:
    def __init__(self, entry: ConfigEntry, config: DeviceConnectConfiguration) -> None:
        self.entry = entry
        self.config = config

    async def initialize_device(self, hass: HomeAssistant) -> bool:
        session = create_aiohttp_session(hass)
        if discover_data := self.entry.data.get(CONF_DISCOVERED_DEVICE_INFO):
            _LOGGER.info("Found discovered data, avoid to guess protocol")
            discovered_device = DiscoveredDevice.from_dict(discover_data)
            device = await discovered_device.get_tapo_device(credentials=self.config.credentials, session=session)
        else:
            device = await connect(config=self.config, session=session)

        await device.update()
        _LOGGER.info("Detected model of %s: %s", str(device.host), str(device.model))
        if isinstance(device, TapoHub):
            hub = HassTapoHub(self.entry, device)
            return await hub.initialize_hub(hass)
        else:
            polling_rate = timedelta(
                seconds=self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
            )
            return await self._initialize_device(hass, device, polling_rate)

    async def _initialize_device(
            self, hass: HomeAssistant, device: TapoDevice, polling_rate: timedelta
    ):
        coordinator = TapoDataCoordinator(hass, device, polling_rate)
        await coordinator.async_config_entry_first_refresh()  # could raise ConfigEntryNotReady
        hass.data[DOMAIN][self.entry.entry_id] = HassTapoDeviceData(
            coordinator=coordinator,
            config_entry_update_unsub=self.entry.add_update_listener(
                _on_options_update_listener
            ),
            child_coordinators=[],
            device=device,
        )

        await hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)
        return True


async def _on_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
