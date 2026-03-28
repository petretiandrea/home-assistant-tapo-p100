from datetime import date, datetime
from typing import Optional, Union, cast

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from plugp100.components.trigger_log import TriggerLogComponent
from plugp100.devices.children.trigger_button import TriggerButtonDevice
from plugp100.devices.children.trv import KE100Device
from plugp100.models.temperature import TemperatureUnit

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        device = child_coordinator.device
        if isinstance(device, KE100Device):
            async_add_entities([TRVTemperatureOffset(child_coordinator, device)], True)
        elif isinstance(device, TriggerButtonDevice) and device.has_component(
            TriggerLogComponent
        ):
            async_add_entities([PollUtilization(child_coordinator, device)], True)


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


DEFAULT_POLL_UTILIZATION = 35  # percent


class PollUtilization(CoordinatedTapoEntity, RestoreNumber):
    """Max hub utilization target for the adaptive polling algorithm.

    Lower = less aggressive polling (more stable, slower response).
    Higher = more aggressive polling (faster response, more hub load).
    The PollLatencySensor reads this value to compute the polling interval.
    """

    _attr_has_entity_name = True
    _attr_name = "Poll Utilization"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:speedometer"
    _attr_native_min_value = 5
    _attr_native_max_value = 50
    _attr_native_step = 5
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        device: TriggerButtonDevice,
    ) -> None:
        super().__init__(coordinator, device)
        self._attr_native_value = float(DEFAULT_POLL_UTILIZATION)

    @property
    def unique_id(self):
        return super().unique_id + "_poll_utilization"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (
            last := await self.async_get_last_number_data()
        ) and last.native_value is not None:
            self._attr_native_value = last.native_value
        # Store on coordinator so PollLatencySensor can read it
        self.coordinator._poll_utilization_pct = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.coordinator._poll_utilization_pct = value
        self.async_write_ha_state()
