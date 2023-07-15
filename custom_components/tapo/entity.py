import logging
from typing import Awaitable, Callable, TypeVar

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import TapoCoordinator

_LOGGER = logging.getLogger(__name__)

State = TypeVar("State")


class BaseTapoEntity(CoordinatorEntity[TapoCoordinator[State]]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoCoordinator[State]):
        super().__init__(coordinator)
        self._base_data = coordinator.get_device_info()
        self._data = coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._base_data.device_id)},
            "name": self._base_data.nickname,
            "model": self._base_data.model,
            "manufacturer": "TP-Link",
            "sw_version": self._base_data and self._base_data.firmware_version,
            "hw_version": self._base_data and self._base_data.hardware_version,
        }

    @property
    def unique_id(self):
        return self._base_data and self._base_data.device_id

    @property
    def name(self):
        return self._base_data and self._base_data.nickname

    @callback
    def _handle_coordinator_update(self) -> None:
        self._data = self.coordinator.data
        self._base_data = self.coordinator.get_device_info()
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
                await self.coordinator.device.login()
                return await self._execute_with_fallback(function, False)
