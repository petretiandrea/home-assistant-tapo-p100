from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.tapo.common_setup import TapoUpdateCoordinator
from custom_components.tapo.tapo_sensor_entity import (
    TapoCurrentEnergySensor,
    TapoSignalSensor,
    TapoTodayEnergySensor,
    TapoMonthEnergySensor,
)
from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR,
)

### Supported sensors: Today energy and current energy
SUPPORTED_SENSOR = [
    TapoTodayEnergySensor,
    TapoMonthEnergySensor,
    TapoCurrentEnergySensor,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    coordinator: TapoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [TapoSignalSensor(coordinator)]

    if coordinator.data.model.lower() in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR:
        sensors.extend([factory(coordinator) for factory in SUPPORTED_SENSOR])

    async_add_devices(sensors, True)
