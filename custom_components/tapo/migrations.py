from custom_components.tapo.const import CONF_MAC
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.setup_helpers import create_api_from_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


async def migrate_entry_to_v8(hass: HomeAssistant, config_entry: ConfigEntry):
    api = await create_api_from_config(hass, config_entry)
    new_data = {**config_entry.data}
    scan_interval = new_data.pop(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
    if mac := (await api.get_device_info()).map(lambda j: j["mac"]).get_or_else(None):
        config_entry.version = 8
        hass.config_entries.async_update_entry(
            config_entry,
            data={
                **new_data,
                CONF_MAC: dr.format_mac(mac),
                CONF_SCAN_INTERVAL: scan_interval,
            },
        )
    else:
        raise Exception("Failed to fetch data to migrate entity")
