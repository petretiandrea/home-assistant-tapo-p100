import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from plugp100.devices import connect
from plugp100.errors.protocol_guess import (
    HostUnreachableError,
    ProtocolDetectionTimeoutError,
)

from custom_components.tapo.const import CONF_HOST, CONF_MAC, DEFAULT_POLLING_RATE_S
from custom_components.tapo.setup_helpers import (
    create_aiohttp_session,
    create_device_config,
)

_LOGGER = logging.getLogger(__name__)


async def migrate_entry_to_v8(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    session = create_aiohttp_session(hass)
    try:
        device = await connect(config=create_device_config(config_entry), session=session)
        await device.update()
    except (HostUnreachableError, ProtocolDetectionTimeoutError) as error:
        # The v8 migration needs to reach the device only to read its MAC. If the
        # device is offline while Home Assistant starts, don't let the exception
        # bubble up (that produces a scary traceback and marks the entry as
        # permanently failed). Fail the migration cleanly instead; Home Assistant
        # retries it on the next restart, when the device is reachable again.
        _LOGGER.error(
            "Cannot migrate Tapo entry '%s' from version %s: device at %s is "
            "unreachable (%s). Migration will be retried on the next restart.",
            config_entry.title,
            config_entry.version,
            config_entry.data.get(CONF_HOST),
            error,
        )
        return False

    new_data = {**config_entry.data}
    scan_interval = new_data.pop(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
    if mac := device.mac:
        hass.config_entries.async_update_entry(
            config_entry,
            data={
                **new_data,
                CONF_MAC: dr.format_mac(mac),
                CONF_SCAN_INTERVAL: scan_interval,
            },
            version=8,
        )
        return True

    _LOGGER.error(
        "Cannot migrate Tapo entry '%s' from version %s: device at %s did not "
        "report a MAC address. Migration will be retried on the next restart.",
        config_entry.title,
        config_entry.version,
        config_entry.data.get(CONF_HOST),
    )
    return False
