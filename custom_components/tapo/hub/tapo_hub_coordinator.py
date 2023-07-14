from datetime import timedelta

from homeassistant.core import HomeAssistant
from plugp100.api.hub.hub_device import HubDevice
from plugp100.common.functional.either import Either
from plugp100.responses.device_state import DeviceInfo, HubDeviceState

from custom_components.tapo.coordinators import SensorState, TapoCoordinator


class TapoHubCoordinator(TapoCoordinator[HubDeviceState]):
    def __init__(
        self,
        hass: HomeAssistant,
        device: HubDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    def get_sensor_state(self) -> SensorState:
        return SensorState(self.data.info, None, None)

    def get_device_info(self) -> DeviceInfo:
        return self.data.info

    async def _get_state_from_device(self) -> Either[HubDeviceState, Exception]:
        return await self.device.get_state()
