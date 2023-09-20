from datetime import timedelta
from typing import TypeVar

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoCoordinator
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.api.hub.s200b_device import S200BDeviceState
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t100_device import T100MotionSensorState
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t110_device import T110SmartDoorState
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.t31x_device import T31DeviceState
from plugp100.api.hub.t31x_device import TemperatureHumidityRecordsRaw

HubChildDevice = (
    T31Device | T100MotionSensor | T110SmartDoor | S200ButtonDevice | T100MotionSensor
)
HubChildCommonState = (
    T31DeviceState | T110SmartDoorState | S200BDeviceState | T100MotionSensorState
)


class TapoHubChildCoordinator(TapoCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        device: HubChildDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    async def _update_state(self):
        if isinstance(self.device, T31Device):
            base_state = (await self.device.get_device_state()).get_or_raise()
            self.update_state_of(HubChildCommonState, base_state)
            self.update_state_of(
                TemperatureHumidityRecordsRaw,
                (await self.device.get_temperature_humidity_records()).get_or_raise(),
            )
        elif isinstance(self.device, T110SmartDoor):
            base_state = (await self.device.get_device_state()).get_or_raise()
            self.update_state_of(HubChildCommonState, base_state)
        elif isinstance(self.device, S200ButtonDevice):
            base_state = (await self.device.get_device_info()).get_or_raise()
            self.update_state_of(HubChildCommonState, base_state)
        elif isinstance(self.device, T100MotionSensor):
            base_state = (await self.device.get_device_state()).get_or_raise()
            self.update_state_of(HubChildCommonState, base_state)


C = TypeVar("C", bound=TapoCoordinator)


class BaseTapoHubChildEntity(CoordinatorEntity[C]):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: C):
        super().__init__(coordinator)
        self._base_data = self.coordinator.get_state_of(HubChildCommonState)

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(identifiers={(DOMAIN, self._base_data.device_id)})

    @property
    def unique_id(self):
        return self._base_data.device_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self._base_data = self.coordinator.get_state_of(HubChildCommonState)
        self.async_write_ha_state()
