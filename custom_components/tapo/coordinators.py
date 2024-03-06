import logging
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

import aiohttp
import async_timeout
from custom_components.tapo.const import Component
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_LED_STRIP
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_LIGHT
from custom_components.tapo.const import SUPPORTED_DEVICE_AS_SWITCH
from custom_components.tapo.const import SUPPORTED_HUB_DEVICE_MODEL
from custom_components.tapo.const import SUPPORTED_POWER_STRIP_DEVICE_MODEL
from custom_components.tapo.const import TapoDevice
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
from plugp100.api.plug_device import PlugDevice
from plugp100.api.power_strip_device import PowerStripDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.responses.components import Components
from plugp100.responses.device_state import DeviceInfo as TapoDeviceInfo
from plugp100.responses.energy_info import EnergyInfo
from plugp100.responses.power_info import PowerInfo
from plugp100.responses.tapo_exception import TapoError
from plugp100.responses.tapo_exception import TapoException

_LOGGER = logging.getLogger(__name__)

DEBOUNCER_COOLDOWN = 2


@dataclass
class HassTapoDeviceData:
    coordinator: "TapoDeviceCoordinator"
    config_entry_update_unsub: CALLBACK_TYPE
    child_coordinators: List["TapoDataCoordinator"]


def create_tapo_device(model: str, client: TapoClient) -> Optional[TapoDevice]:
    if model in SUPPORTED_DEVICE_AS_SWITCH:
        return PlugDevice(client)
    if model in SUPPORTED_DEVICE_AS_LED_STRIP:
        return LedStripDevice(client)
    if model in SUPPORTED_DEVICE_AS_LIGHT:
        return LightDevice(client)
    if model in SUPPORTED_POWER_STRIP_DEVICE_MODEL:
        return PowerStripDevice(client)
    if model in SUPPORTED_HUB_DEVICE_MODEL:
        return HubDevice(client, subscription_polling_interval_millis=30_000)
    return None


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
        self.components: Components | None = None

    async def _negotiate_components_if_needed(self):
        if self.components is None:
            self.components = (
                await self.device.get_component_negotiation()
            ).get_or_raise()

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
    def is_hub(self) -> bool:
        return isinstance(self.device, HubDevice)

    @property
    def device_info(self) -> TapoDeviceInfo:
        return self.get_state_of(TapoDeviceInfo)

    @abstractmethod
    async def _update_state(self) -> None:
        pass

    async def _async_update_data(self) -> StateMap:
        try:
            async with async_timeout.timeout(10):
                await self._negotiate_components_if_needed()
                return await self._update_state()
        except TapoException as error:
            _raise_from_tapo_exception(error)
        except aiohttp.ClientError as error:
            raise UpdateFailed(f"Error communication with API: {str(error)}") from error
        except Exception as exception:
            raise UpdateFailed(f"Unexpected exception: {str(exception)}") from exception


PowerStripChildrenState = dict[str, PowerStripChild]


class TapoDeviceCoordinator(TapoDataCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        device: TapoDevice,
        polling_interval: timedelta,
    ):
        super().__init__(hass, device, polling_interval)

    async def _update_state(self):
        # fetch base state based on device type
        # fetch additional data based on negotiated components
        state = (await self.device.get_state()).get_or_raise()
        self.update_state_of(type(state), state)
        self.update_state_of(TapoDeviceInfo, state.info)

        if self.components.has(Component.ENERGY_MONITORING.value):
            power_info = value_optional(await self.device.get_current_power())
            energy_usage = value_optional(await self.device.get_energy_usage())
            self.update_state_of(PowerInfo, power_info)
            self.update_state_of(EnergyInfo, energy_usage)

        if self.components.has(Component.CONTROL_CHILD.value) and isinstance(
            self.device, PowerStripDevice
        ):
            children_state = (await self.device.get_children()).get_or_raise()
            self.update_state_of(PowerStripChildrenState, children_state)


def _raise_from_tapo_exception(exception: TapoException):
    _LOGGER.error("Tapo exception: %s", str(exception))
    if exception.error_code == TapoError.INVALID_CREDENTIAL.value:
        raise ConfigEntryAuthFailed from exception
    else:
        raise UpdateFailed(f"Error tapo exception: {exception}") from exception
