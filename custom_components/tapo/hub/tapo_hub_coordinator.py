from datetime import timedelta

from homeassistant.core import HomeAssistant
from plugp100.api.hub.hub_device import HubDevice
from plugp100.responses.device_state import DeviceInfo, HubDeviceState

from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.helpers import value_or_raise


class TapoHubCoordinator(TapoCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        device: HubDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    async def _update_state(self):
        hub_state = value_or_raise(await self.device.get_state())
        self.update_state_of(
            HubDeviceState, value_or_raise(await self.device.get_state())
        )
        self.update_state_of(DeviceInfo, hub_state.info)
