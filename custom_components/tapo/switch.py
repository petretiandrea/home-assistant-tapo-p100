from typing import Any, Dict, Optional, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.plug_device import PlugDevice

from custom_components.tapo import HassTapoDeviceData
from custom_components.tapo.common_setup import (
    TapoCoordinator,
    setup_tapo_coordinator_from_dictionary,
)
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import (
    PlugDeviceState,
    PlugTapoCoordinator,
    TapoCoordinator,
)
from custom_components.tapo.tapo_entity import TapoEntity
from custom_components.tapo.utils import value_or_raise


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    coordinator = value_or_raise(
        await setup_tapo_coordinator_from_dictionary(hass, config)
    )
    _setup_from_coordinator(coordinator, async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    _setup_from_coordinator(data.coordinator, async_add_devices)


def _setup_from_coordinator(
    coordinator: TapoCoordinator, async_add_devices: AddEntitiesCallback
):
    if isinstance(coordinator, PlugTapoCoordinator):
        async_add_devices([TapoPlugEntity(coordinator)], True)


class TapoPlugEntity(TapoEntity[PlugDeviceState], SwitchEntity):
    def __init__(self, coordinator: PlugTapoCoordinator):
        super().__init__(coordinator)
        self.device: PlugDevice = coordinator.device

    @property
    def is_on(self) -> Optional[bool]:
        return self.last_state and self.last_state.device_on

    async def async_turn_on(self, **kwargs):
        value_or_raise(await self.device.on())
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        value_or_raise(await self.device.off())
        await self.coordinator.async_request_refresh()
