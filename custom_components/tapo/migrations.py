from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_MAC
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.setup_helpers import connect_tapo_client
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from plugp100.common.credentials import AuthCredential


async def migrate_entry_to_v6(hass: HomeAssistant, config_entry: ConfigEntry):
    credential = AuthCredential(
        config_entry.data.get(CONF_USERNAME), config_entry.data.get(CONF_PASSWORD)
    )
    api = await connect_tapo_client(
        hass, credential, config_entry.data.get(CONF_HOST), config_entry.unique_id
    )
    new_data = {**config_entry.data}
    scan_interval = new_data.pop(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
    mac = (await api.get_device_info()).map(lambda j: j["mac"]).get_or_else(None)
    config_entry.version = 6
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            **new_data,
            CONF_MAC: mac,
            CONF_TRACK_DEVICE: False,
            CONF_SCAN_INTERVAL: scan_interval,
        },
    )
