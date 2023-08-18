from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Optional, TypeVar, Union, cast

import aiohttp
import async_timeout
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.ledstrip_device import LedStripDevice
from plugp100.api.light_device import LightDevice
from plugp100.api.power_strip_device import PowerStripDevice
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.api.plug_device import EnergyInfo, PlugDevice, PowerInfo
from plugp100.api.tapo_client import TapoClient
from plugp100.common.functional.either import Either, Right, Left
from typing import Type, TypeVar, Dict, List, cast
from plugp100.responses.device_state import (
    DeviceInfo,
    LedStripDeviceState,
    LightDeviceState,
    PlugDeviceState,
)
from plugp100.responses.tapo_exception import TapoError, TapoException

from custom_components.tapo.const import (
    DOMAIN,
    SUPPORTED_DEVICE_AS_LED_STRIP,
    SUPPORTED_DEVICE_AS_LIGHT,
    SUPPORTED_DEVICE_AS_SWITCH,
    SUPPORTED_POWER_STRIP_DEVICE_MODEL,
)

from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.helpers import (
    get_short_model,
    value_optional,
    value_or_raise,
)

_LOGGER = logging.getLogger(__name__)

TapoDevice = Union[LightDevice, PlugDevice, LedStripDevice, HubDevice, PowerStripDevice]

DEBOUNCER_COOLDOWN = 2


@dataclass
class HassTapoDeviceData:
    coordinator: "TapoCoordinator"
    config_entry_update_unsub: CALLBACK_TYPE


async def create_coordinator(
    hass: HomeAssistant, client: TapoClient, host: str, polling_interval: timedelta
) -> Either["TapoCoordinator", Exception]:
    logged_in = await client.login(host)
    _LOGGER.info("Login to %s, success: %s", str(host), str(logged_in))
    model_or_error = (
        (await client.get_device_info())
        .map(lambda x: DeviceInfo(**x))
        .map(lambda info: get_short_model(info.model))
    )
    _LOGGER.info("Detected model of %s: %s", str(host), str(model_or_error))

    if isinstance(model_or_error, Right):
        if model_or_error.value in SUPPORTED_DEVICE_AS_SWITCH:
            return Right(
                PlugTapoCoordinator(hass, PlugDevice(client, host), polling_interval)
            )
        elif model_or_error.value in SUPPORTED_DEVICE_AS_LED_STRIP:
            return Right(
                LightTapoCoordinator(
                    hass, LedStripDevice(client, host), polling_interval
                )
            )
        elif model_or_error.value in SUPPORTED_DEVICE_AS_LIGHT:
            return Right(
                LightTapoCoordinator(hass, LightDevice(client, host), polling_interval)
            )
        # elif model_or_error.value == SUPPORTED_POWER_STRIP_DEVICE_MODEL:
        #     return Right(
        #         PowerStripCoordinator(
        #             hass, PowerStripDevice(client, host), polling_interval
        #         )
        #     )
        else:
            return Left(DeviceNotSupported(f"Device {host} not supported!"))

    return model_or_error


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
    def device_info(self) -> DeviceInfo:
        return self.get_state_of(DeviceInfo)

    @abstractmethod
    async def _update_state(self) -> None:
        pass

    async def _async_update_data(self) -> StateMap:
        try:
            async with async_timeout.timeout(10):
                return await self._update_with_fallback(retry=True)
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception

    async def _update_with_fallback(self, retry=True):
        try:
            return await self._update_state()
        except Exception:  # pylint: disable=broad-except
            if retry:
                value_or_raise(await self._device.login())
                return await self._update_with_fallback(False)

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
        self.has_power_monitor = False

    def enable_power_monitor(self):
        self.has_power_monitor = True

    async def _update_state(self):
        plug = cast(PlugDevice, self.device)
        plug_state = value_or_raise(await plug.get_state())
        self.update_state_of(PlugDeviceState, plug_state)
        self.update_state_of(DeviceInfo, plug_state.info)
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
        state = value_or_raise(await self.device.get_state())
        self.update_state_of(DeviceInfo, state.info)
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


@dataclass
class PowerStripState:
    device_info: DeviceInfo
    children_state: dict[str, PowerStripChild]


class PowerStripCoordinator(TapoCoordinator[PowerStripState]):
    def __init__(
        self, hass: HomeAssistant, device: PowerStripDevice, polling_interval: timedelta
    ):
        super().__init__(hass, device, polling_interval)

    def get_device_info(self) -> DeviceInfo:
        return self.data.device_info

    def get_children(self) -> list[PowerStripChild]:
        return self.data.children_state

    async def _get_state_from_device(self) -> Either[PowerStripState, Exception]:
        children_state = value_or_raise(
            await cast(PowerStripDevice, self.device).get_children()
        ).get_children(lambda x: PowerStripChild.try_from_json(**x))
        return PowerStripState(
            device_info=value_or_raise(
                await cast(PowerStripDevice, self.device).get_state()
            ).info,
            children_state={child.device_id: child for child in children_state},
        )

    def get_child_state(self, device_id: str) -> PowerStripChild:
        return self.data.children_state.get(device_id)
