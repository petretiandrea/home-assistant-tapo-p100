from typing import Any
from typing import cast

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.hub.tapo_hub_child_coordinator import BaseTapoHubChildEntity
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.responses.hub_childs.ke100_device_state import TRVState
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


class TRVClimate(BaseTapoHubChildEntity, ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = "Climate"

    def __init__(self, coordinator: TapoCoordinator):
        super().__init__(coordinator)

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def hvac_modes(self) -> HVACMode | None:
        return [HVACMode.OFF, HVACMode.HEAT]

    @property
    def min_temp(self) -> float:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .min_control_temperature
        )

    @property
    def max_temp(self) -> float:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .max_control_temperature
        )

    @property
    def current_temperature(self) -> float | None:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .current_temperature
        )

    @property
    def target_temperature(self) -> float | None:
        return (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .target_temperature
        )

    @property
    def temperature_unit(self) -> str:
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

    @property
    def hvac_mode(self) -> HVACMode | None:
        trv_state = (
            cast(TapoCoordinator, self.coordinator)
            .get_state_of(HubChildCommonState)
            .trv_state
        )

        if trv_state == TRVState.HEATING:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    # Kasa seems to use Frost Protection to turn the TRV On and Off
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            (
                await cast(
                    TapoCoordinator, self.coordinator
                ).device.set_frost_protection_off()
            ).get_or_raise()
        else:
            (
                await cast(
                    TapoCoordinator, self.coordinator
                ).device.set_frost_protection_on()
            ).get_or_raise()

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        (
            await cast(TapoCoordinator, self.coordinator).device.set_target_temp(kwargs)
        ).get_or_raise()
        await self.coordinator.async_request_refresh()


SENSOR_MAPPING = {KE100Device: [TRVClimate]}
