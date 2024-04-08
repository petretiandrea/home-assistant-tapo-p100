from datetime import date
from datetime import datetime
from typing import Optional
from typing import Union
from typing import cast

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number import NumberEntity
from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.new.child.tapohubchildren import KE100Device
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        device = child_coordinator.device
        if isinstance(device, KE100Device):
            async_add_entities(
                [TRVTemperatureOffset(child_coordinator, device)],
                True
            )


class TRVTemperatureOffset(CoordinatedTapoEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Temperature Offset"

    device: KE100Device

    def __init__(
            self,
            coordinator: TapoDataCoordinator,
            device: KE100Device,
    ) -> None:
        super().__init__(coordinator, device)

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
        return self.device.temperature_offset

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        if self.device.temperature_unit == TemperatureUnit.CELSIUS:
            return UnitOfTemperature.CELSIUS
        elif self.device.temperature_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        else:
            return None

    async def async_set_native_value(self, value: float) -> None:
        (await self.device.set_temp_offset(int(value))).get_or_raise()
        await self.coordinator.async_request_refresh()
