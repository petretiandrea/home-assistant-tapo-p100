from typing import Any, Optional, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.helpers import value_or_raise
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    async_add_devices([AlarmSwitch(data.coordinator)], True)


class AlarmSwitch(CoordinatorEntity[TapoHubCoordinator], SwitchEntity):
    def __init__(self, coordinator: TapoHubCoordinator, context: Any = None) -> None:
        super().__init__(coordinator, context)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return self.coordinator.data and self.coordinator.data.info.device_id

    @property
    def name(self):
        return self.coordinator.data and f"{self.coordinator.data.info.nickname} Alarm"

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.data.info.device_id)})

    @property
    def is_on(self) -> Optional[bool]:
        return self.coordinator.data and self.coordinator.data.in_alarm

    async def async_turn_on(self, **kwargs):
        value_or_raise(await self.coordinator.device.turn_alarm_on())
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        value_or_raise(await self.coordinator.device.turn_alarm_off())
        await self.coordinator.async_request_refresh()
