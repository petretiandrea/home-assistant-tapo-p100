from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.tapo.hub.siren import async_setup_entry as async_setup_hub_siren


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # get tapo helper
    if entry.data.get("is_hub", False):
        await async_setup_hub_siren(hass, entry, async_add_entities)
