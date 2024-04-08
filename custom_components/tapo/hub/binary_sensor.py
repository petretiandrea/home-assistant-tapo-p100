from typing import Optional
from typing import cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.new.components.battery_component import BatteryComponent
from plugp100.new.components.motion_sensor_component import MotionSensorComponent
from plugp100.new.components.smart_door_component import SmartDoorComponent
from plugp100.new.components.water_leak_component import WaterLeakComponent
from plugp100.new.tapodevice import TapoDevice

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity

COMPONENT_MAPPING = {
    SmartDoorComponent: 'SmartDoorSensor',
    WaterLeakComponent: 'WaterLeakSensor',
    MotionSensorComponent: 'MotionSensor',
    BatteryComponent: 'LowBatterySensor'
}


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensors = [
            eval(cls)(child_coordinator, child_coordinator.device)
            for (component, cls) in COMPONENT_MAPPING.items()
            if child_coordinator.device.has_component(component)
        ]
        async_add_entities(sensors, True)


class SmartDoorSensor(CoordinatedTapoEntity, BinarySensorEntity):
    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.DOOR

    @property
    def is_on(self) -> bool:
        return self.device.get_component(SmartDoorComponent).is_open


class WaterLeakSensor(CoordinatedTapoEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self) -> bool:
        return self.device.get_component(WaterLeakComponent).water_leak_status != "normal"


class MotionSensor(CoordinatedTapoEntity, BinarySensorEntity):
    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool:
        return self.device.get_component(MotionSensorComponent).detected


class LowBatterySensor(CoordinatedTapoEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: TapoDevice
    ):
        super().__init__(coordinator, device)
        self._attr_name = "Battery Low"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> Optional[str]:
        return BinarySensorDeviceClass.BATTERY

    @property
    def is_on(self) -> bool:
        return self.device.get_component(BatteryComponent).is_battery_low
