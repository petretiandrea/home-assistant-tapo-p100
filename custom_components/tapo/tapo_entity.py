import logging
from typing import Callable, Awaitable, Optional, TypeVar
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100 import TapoDeviceState
from custom_components.tapo.common_setup import TapoCoordinator
from custom_components.tapo.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TapoEntity(CoordinatorEntity):
    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)
        self._data = coordinator.data

    @property
    def _tapo_coordinator(self) -> TapoCoordinator:
        return self.coordinator

    @property
    def last_state(self) -> Optional[TapoDeviceState]:
        return self._data

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.last_state.device_id)},
            "name": self.last_state.nickname,
            "model": self.last_state.model,
            "manufacturer": "TP-Link",
            "sw_version": self.last_state and self.last_state.firmware_version,
            "hw_version": self.last_state and self.last_state.hardware_version,
        }

    @property
    def unique_id(self):
        return self.last_state and self.last_state.device_id

    @property
    def name(self):
        return self.last_state and self.last_state.nickname

    @callback
    def _handle_coordinator_update(self) -> None:
        self._data = self._tapo_coordinator.data
        self.async_write_ha_state()

    T = TypeVar("T")

    async def _execute_with_fallback(
        self, function: Callable[[], Awaitable[T]], retry=True
    ) -> T:
        try:
            return await function()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Error during command execution %s", str(error))
            if retry:
                await self.coordinator.api.login()
                return await self._execute_with_fallback(function, False)
