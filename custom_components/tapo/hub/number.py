from datetime import date
from datetime import datetime
from typing import cast
from typing import Optional
from typing import Union

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number import NumberEntity
from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.responses.temperature_unit import TemperatureUnit


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        sensor_factories = SENSOR_MAPPING.get(type(child_coordinator.device), [])
        async_add_entities(
            [factory(child_coordinator) for factory in sensor_factories], True
        )


class TRVTemperatureOffset(BaseTapoHubChildEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Temperature Offset"

    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def device_class(self) -> NumberDeviceClass | None:
        return NumberDeviceClass.TEMPERATURE

    @property
    def native_min_value(self) -> float:
        return -10

    @property
    def native_max_value(self) -> float:
        return 10

    @property
    def mode(self) -> NumberMode:
        return NumberMode.AUTO

    @property
    def native_step(self) -> float | None:
        return 1

    @property
    def native_value(self) -> Union[StateType, date, datetime]:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .temperature_offset
        )

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        temp_unit = (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .temperature_unit
        )
        if temp_unit == TemperatureUnit.CELSIUS:
            return UnitOfTemperature.CELSIUS
        elif temp_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        else:
            return None

    async def async_set_native_value(self, value: float) -> None:
        (
            await cast(TapoCoordinator, self.coordinator).device.set_temp_offset(
                int(value)
            )
        ).get_or_raise()
        await self.coordinator.async_request_refresh()


SENSOR_MAPPING = {KE100Device: [TRVTemperatureOffset]}
