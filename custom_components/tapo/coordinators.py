from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Optional, TypeVar, Union

import aiohttp
import async_timeout
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.ledstrip_device import LedStripDevice
from plugp100.api.light_device import LightDevice
from plugp100.api.plug_device import EnergyInfo, PlugDevice, PowerInfo
from plugp100.api.tapo_client import TapoClient
from plugp100.common.functional.either import Either, Right, Left
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
)
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.helpers import get_short_model, value_or_raise

_LOGGER = logging.getLogger(__name__)

TapoDevice = Union[LightDevice, PlugDevice, LedStripDevice, HubDevice]

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
        else:
            return Left(DeviceNotSupported(f"Device {host} not supported!"))

    return model_or_error


@dataclass
class SensorState:
    info: DeviceInfo
    power_info: Optional[PowerInfo]
    energy_info: Optional[EnergyInfo]


State = TypeVar("State")


class TapoCoordinator(ABC, DataUpdateCoordinator[State]):
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

    @property
    def device(self) -> TapoDevice:
        return self._device

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        pass

    @abstractmethod
    def get_sensor_state(self) -> SensorState:
        pass

    async def _get_state_from_device(self) -> Either[State, Exception]:
        return await self._device.get_state()

    async def _async_update_data(self) -> State:
        try:
            async with async_timeout.timeout(10):
                return await self._update_with_fallback()
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception

    async def _update_with_fallback(self, retry=True):
        try:
            return value_or_raise(await self._get_state_from_device())
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


class PlugTapoCoordinator(TapoCoordinator[PlugDeviceState]):
    def __init__(
        self,
        hass: HomeAssistant,
        device: PlugDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)
        self.has_power_monitor = False
        self.power_info = None
        self.energy_info = None

    def enable_power_monitor(self):
        self.has_power_monitor = True

    def get_device_info(self) -> DeviceInfo:
        return self.data.info

    def get_sensor_state(self) -> SensorState:
        return SensorState(self.data.info, self.power_info, self.energy_info)

    async def _get_state_from_device(self) -> Either[PlugDeviceState, Exception]:
        self.power_info = (
            (await self.device.get_current_power()).fold(lambda x: x, lambda _: None)
            if self.has_power_monitor
            else None
        )
        self.energy_info = (
            (await self.device.get_energy_usage()).fold(lambda x: x, lambda _: None)
            if self.has_power_monitor
            else None
        )
        return await self.device.get_state()


class LightTapoCoordinator(
    TapoCoordinator[Union[LightDeviceState, LedStripDeviceState]]
):
    def __init__(
        self,
        hass: HomeAssistant,
        device: Union[LightDevice, LedStripDevice],
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    def get_device_info(self) -> DeviceInfo:
        return self.data.info

    def get_sensor_state(self) -> SensorState:
        return SensorState(self.data.info, None, None)
