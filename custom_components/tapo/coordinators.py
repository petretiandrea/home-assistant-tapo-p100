import logging
from abc import ABC
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Type
from typing import TypeVar

import aiohttp
import async_timeout
from homeassistant.core import CALLBACK_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from plugp100.new.tapodevice import TapoDevice
from plugp100.new.tapohub import TapoHub
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.responses.tapo_exception import TapoException

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.helpers import _raise_from_tapo_exception

_LOGGER = logging.getLogger(__name__)

DEBOUNCER_COOLDOWN = 2


@dataclass
class HassTapoDeviceData:
    device: TapoDevice
    coordinator: "TapoDataCoordinator"
    config_entry_update_unsub: CALLBACK_TYPE
    child_coordinators: List["TapoDataCoordinator"]


# def create_tapo_device(model: str, client: TapoClient) -> Optional[TapoDevice]:
#     if model in SUPPORTED_DEVICE_AS_SWITCH:
#         return PlugDevice(client)
#     if model in SUPPORTED_DEVICE_AS_LED_STRIP:
#         return LedStripDevice(client)
#     if model in SUPPORTED_DEVICE_AS_LIGHT:
#         return LightDevice(client)
#     if model in SUPPORTED_POWER_STRIP_DEVICE_MODEL:
#         return PowerStripDevice(client)
#     if model in SUPPORTED_HUB_DEVICE_MODEL:
#         return HubDevice(client, subscription_polling_interval_millis=30_000)
#     return None


T = TypeVar("T")

StateMap = Dict[Type[T], T]


class TapoDataCoordinator(ABC, DataUpdateCoordinator[StateMap]):
    def __init__(
            self,
            hass: HomeAssistant,
            device: TapoDevice,
            polling_interval: timedelta,
    ):
        self._device = device
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=polling_interval,
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=DEBOUNCER_COOLDOWN, immediate=True
            ),
        )
        self._states: StateMap = {}
        # TODO: expose .state from self.device as raw json

    @property
    def device(self) -> TapoDevice:
        return self._device

    @property
    def is_hub(self) -> bool:
        return isinstance(self.device, TapoHub)

    async def _async_update_data(self) -> StateMap:
        try:
            async with async_timeout.timeout(10):
                return await self.poll_update()
        except TapoException as error:
            _raise_from_tapo_exception(error, _LOGGER)
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception

    async def poll_update(self):
        return await self.device.update()


PowerStripChildrenState = dict[str, PowerStripChild]
