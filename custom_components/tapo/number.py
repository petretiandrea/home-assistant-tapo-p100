from typing import cast

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.hub.number import (
    async_setup_entry as async_setup_hub_number,
)
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if isinstance(data.coordinator, TapoHubCoordinator):
        await async_setup_hub_number(hass, entry, async_add_entities)
