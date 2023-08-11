from math import floor
from typing import Any, Optional, cast

from homeassistant.components.siren import (
    ATTR_TONE,
    ATTR_VOLUME_LEVEL,
    SirenEntity,
    SirenEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from plugp100.requests.set_device_info.play_alarm_params import PlayAlarmParams

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.helpers import clamp, value_or_raise
from custom_components.tapo.hub.tapo_hub_coordinator import TapoHubCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    available_tones = value_or_raise(
        await data.coordinator.device.get_supported_alarm_tones()
    ).tones
    async_add_devices([HubSiren(data.coordinator, available_tones)], True)


class HubSiren(CoordinatorEntity[TapoHubCoordinator], SirenEntity):
    _attr_has_entity_name = True
    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.VOLUME_SET
        | SirenEntityFeature.TONES
    )

    def __init__(
        self, coordinator: TapoHubCoordinator, tones: list[str], context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self._attr_available_tones = tones

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return self.coordinator.data and self.coordinator.data.info.device_id

    @property
    def name(self):
        return "Siren"

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.data.info.device_id)})

    @property
    def is_on(self) -> Optional[bool]:
        return self.coordinator.data and self.coordinator.data.in_alarm

    async def async_turn_on(self, **kwargs):
        volume = _map_volume_to_discrete_values(
            kwargs.get(ATTR_VOLUME_LEVEL, 1.0), "mute", ["low", "normal", "high"]
        )
        tone = kwargs.get(ATTR_TONE, None)
        play_alarm = PlayAlarmParams(alarm_volume=volume, alarm_type=tone)
        value_or_raise(await self.coordinator.device.turn_alarm_on(play_alarm))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        value_or_raise(await self.coordinator.device.turn_alarm_off())
        await self.coordinator.async_request_refresh()


def _map_volume_to_discrete_values(
    volume: float, mute: str, supported_values: list[str]
) -> str:
    if volume > 0:
        step = 1.0 / (len(supported_values) - 1)
        index = floor(volume / step)
        return supported_values[index]
    else:
        return mute
