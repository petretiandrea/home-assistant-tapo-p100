from typing import Any, Optional
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from custom_components.tapo.common_setup import (
    TapoCoordinator,
    setup_tapo_coordinator_from_dictionary,
)
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    # get tapo helper
    coordinator: TapoCoordinator = hass.data[DOMAIN][entry.entry_id]
    _setup_from_coordinator(coordinator, async_add_devices)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Any,
) -> None:
    coordinator = await setup_tapo_coordinator_from_dictionary(hass, config)
    _setup_from_coordinator(coordinator, async_add_entities)


def _setup_from_coordinator(
    coordinator: TapoCoordinator, async_add_devices: AddEntitiesCallback
):
    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH:
        async_add_devices([TapoPlug(coordinator)], True)


class TapoPlug(TapoEntity, SwitchEntity):
    @property
    def is_on(self) -> Optional[bool]:
        return self.last_state and self.last_state.device_on

    async def async_turn_on(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.on)
        await self._tapo_coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._execute_with_fallback(self._tapo_coordinator.api.off)
        await self._tapo_coordinator.async_request_refresh()
