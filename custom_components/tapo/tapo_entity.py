from typing import Union, Callable, Awaitable, TypeVar

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from . import TapoUpdateCoordinator


class TapoEntity(CoordinatorEntity):
    def __init__(self, coordiantor: TapoUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordiantor)

    @property
    def _tapo_coordinator(self) -> TapoUpdateCoordinator:
        return self.coordinator

    @property
    def unique_id(self):
        return self.coordinator.data.device_id

    @property
    def name(self):
        return self.coordinator.data.nickname

    T = TypeVar("T")

    async def _execute_with_fallback(
        self, function: Callable[[], Awaitable[T]], retry=True
    ) -> T:
        try:
            return await function()
        except Exception:
            await self.coordinator.api.login()
            return await self._execute_with_fallback(function, False)
