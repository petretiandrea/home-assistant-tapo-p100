import logging
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union

import aiohttp
import async_timeout
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_LED_STRIP
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_LIGHT
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_SWITCH
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR
from custom_components.tapo.const import SUPPORTED_POWER_STRIP_DEVICE_MODEL
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.helpers import get_short_model
from custom_components.tapo.helpers import value_optional
from homeassistant.core import CALLBACK_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.ledstrip_device import LedStripDevice
from plugp100.api.light_device import LightDevice
from plugp100.api.plug_device import EnergyInfo
from plugp100.api.plug_device import PlugDevice
from plugp100.api.plug_device import PowerInfo
from plugp100.api.power_strip_device import PowerStripDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.common.functional.tri import Failure
from plugp100.common.functional.tri import Try
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.responses.device_state import DeviceInfo as TapoDeviceInfo
from plugp100.responses.device_state import LedStripDeviceState
from plugp100.responses.device_state import LightDeviceState
from plugp100.responses.device_state import PlugDeviceState
from plugp100.responses.tapo_exception import TapoError
from plugp100.responses.tapo_exception import TapoException

_LOGGER = logging.getLogger(__name__)

TapoDevice = Union[LightDevice, PlugDevice, LedStripDevice, HubDevice, PowerStripDevice]

DEBOUNCER_COOLDOWN = 2


@dataclass
class HassTapoDeviceData:
    coordinator: "TapoCoordinator"
    config_entry_update_unsub: CALLBACK_TYPE
    child_coordinators: List["TapoCoordinator"]


async def create_coordinator(
    hass: HomeAssistant, client: TapoClient, host: str, polling_interval: timedelta
) -> Try["TapoCoordinator"]:
    device_info = (await client.get_device_info()).map(lambda x: TapoDeviceInfo(**x))
    if device_info.is_success():
        model = get_short_model(device_info.get().model)
        _LOGGER.info("Detected model of %s: %s", str(host), str(model))
        if model in SUPPORTED_DEVICE_AS_SWITCH:
            return Try.of(
                PlugTapoCoordinator(hass, PlugDevice(client), polling_interval)
            )
        elif model in SUPPORTED_DEVICE_AS_LED_STRIP:
            return Try.of(
                LightTapoCoordinator(hass, LedStripDevice(client), polling_interval)
            )
        elif model in SUPPORTED_DEVICE_AS_LIGHT:
            return Try.of(
                LightTapoCoordinator(hass, LightDevice(client), polling_interval)
            )
        elif model == SUPPORTED_POWER_STRIP_DEVICE_MODEL:
            return Try.of(
                PowerStripCoordinator(hass, PowerStripDevice(client), polling_interval)
            )
        else:
            return Failure(DeviceNotSupported(f"Device {host} not supported!"))

    return device_info


T = TypeVar("T")

StateMap = Dict[Type[T], T]


class TapoCoordinator(ABC, DataUpdateCoordinator[StateMap]):
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

    @property
    def device(self) -> TapoDevice:
        return self._device

    def has_capability(self, target_type: Type[T]) -> bool:
        return target_type in self._states

    def get_state_of(self, target_type: Type[T]) -> T:
        return self._states.get(target_type)

    def update_state_of(self, target_type: Type[T], state: Optional[T]) -> StateMap:
        if target_type is not None and state is not None:
            self._states[target_type] = state
        return self._states

    @property
    def model(self) -> str:
        return self.get_state_of(TapoDeviceInfo).model.lower()

    @property
    def device_info(self) -> TapoDeviceInfo:
        return self.get_state_of(TapoDeviceInfo)

    @abstractmethod
    async def _update_state(self) -> None:
        pass

    async def _async_update_data(self) -> StateMap:
        try:
            async with async_timeout.timeout(10):
                return await self._update_state()
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception

    def _raise_from_tapo_exception(self, exception: TapoException):
        _LOGGER.error("Tapo exception: %s", str(exception))
        if exception.error_code == TapoError.INVALID_CREDENTIAL.value:
            raise ConfigEntryAuthFailed from exception
        else:
            raise UpdateFailed(f"Error tapo exception: {exception}") from exception


class PlugTapoCoordinator(TapoCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        device: PlugDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    @cached_property
    def has_power_monitor(self) -> bool:
        return (
            get_short_model(self.get_state_of(TapoDeviceInfo).model)
            in SUPPORTED_DEVICE_AS_SWITCH_POWER_MONITOR
        )

    async def _update_state(self):
        plug = cast(PlugDevice, self.device)
        plug_state = (await plug.get_state()).get_or_raise()
        self.update_state_of(PlugDeviceState, plug_state)
        self.update_state_of(TapoDeviceInfo, plug_state.info)
        if self.has_power_monitor:
            power_info = value_optional(await plug.get_current_power())
            energy_usage = value_optional(await plug.get_energy_usage())
            self.update_state_of(PowerInfo, power_info)
            self.update_state_of(EnergyInfo, energy_usage)


class LightTapoCoordinator(TapoCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        device: Union[LightDevice, LedStripDevice],
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    async def _update_state(self):
        state = (await self.device.get_state()).get_or_raise()
        self.update_state_of(TapoDeviceInfo, state.info)
        if isinstance(self.device, LightDevice):
            self.update_state_of(LightDeviceState, state)
        elif isinstance(self.device, LedStripDevice):
            self.update_state_of(LedStripDeviceState, state)

    @property
    def light_state(self):
        return (
            self.get_state_of(LightDeviceState)
            if self.has_capability(LightDeviceState)
            else self.get_state_of(LedStripDeviceState)
        )


PowerStripChildrenState = dict[str, PowerStripChild]


class PowerStripCoordinator(TapoCoordinator):
    def __init__(
        self, hass: HomeAssistant, device: PowerStripDevice, polling_interval: timedelta
    ):
        super().__init__(hass, device, polling_interval)

    async def _update_state(self):
        strip_state = (await self.device.get_state()).get_or_raise()
        children_state = (await self.device.get_children()).get_or_raise()
        self.update_state_of(TapoDeviceInfo, strip_state.info)
        self.update_state_of(PowerStripChildrenState, children_state)

    def get_children(self) -> list[PowerStripChild]:
        return list(self.get_state_of(PowerStripChildrenState).values())

    def get_child_state(self, device_id: str) -> PowerStripChild:
        return self.get_state_of(PowerStripChildrenState).get(device_id)
