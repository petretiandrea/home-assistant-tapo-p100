from typing import cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from plugp100.new.components.overheat_component import OverheatComponent
from plugp100.new.tapodevice import TapoDevice

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity
from custom_components.tapo.hub.binary_sensor import async_setup_entry as async_setup_binary_sensors


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if data.device.has_component(OverheatComponent):
        async_add_devices([OverheatSensor(data.coordinator, data.device)], True)
    if data.coordinator.is_hub:
        await async_setup_binary_sensors(hass, entry, async_add_devices)


class OverheatSensor(CoordinatedTapoEntity, BinarySensorEntity):
    def __init__(self, coordinator: TapoDataCoordinator, device: TapoDevice):
        super().__init__(coordinator, device)
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
        return self.coordinator.device.overheated
