from typing import cast

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.hub.binary_sensor import (
    async_setup_entry as async_setup_binary_sensors,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from plugp100.responses.device_state import DeviceInfo


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    sensors = [OverheatSensor(data.coordinator)]
    async_add_devices(sensors, True)
    if data.coordinator.is_hub:
        await async_setup_binary_sensors(hass, entry, async_add_devices)


class OverheatSensor(CoordinatedTapoEntity[TapoDataCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: TapoDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Overheat"
        self._attr_icon = "mdi:fire-alert"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        return BinarySensorDeviceClass.HEAT

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.get_state_of(DeviceInfo).overheated
