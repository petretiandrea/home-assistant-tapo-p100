from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.tapo.common_setup import TapoUpdateCoordinator
from custom_components.tapo.tapo_sensor_entity import (
    TapoOverheatSensor,
)
from custom_components.tapo.const import (
    DOMAIN,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [TapoOverheatSensor(coordinator)]
    async_add_devices(sensors, True)
