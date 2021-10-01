from typing import Callable, Dict, Any
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from custom_components.tapo.common_setup import (
    TapoUpdateCoordinator,
    setup_tapo_coordinator_from_dictionary,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _setup_from_coordinator(coordinator, async_add_devices)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: Callable,
    discovery_info=None,
) -> None:
    coordinator = await setup_tapo_coordinator_from_dictionary(hass, config)
    _setup_from_coordinator(coordinator, async_add_entities)


def _setup_from_coordinator(coordinator: TapoUpdateCoordinator, async_add_devices):
    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH:
        switch = P100Switch(coordinator)
        async_add_devices([switch], True)


class P100Switch(TapoEntity, SwitchEntity):
    @property
    def is_on(self):
        return self._tapo_coordinator.data.device_on

    async def async_turn_on(self):
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._tapo_coordinator.async_request_refresh()

    async def async_turn_off(self):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_request_refresh()
