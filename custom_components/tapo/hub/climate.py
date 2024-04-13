from typing import Any, Optional
from typing import cast

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.new.child.tapohubchildren import KE100Device
from plugp100.responses.hub_childs.ke100_device_state import TRVState
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
            async_add_entities([TRVClimate(child_coordinator, device)], True)


class TRVClimate(CoordinatedTapoEntity, ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = "Climate"

    device: KE100Device

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        device: KE100Device,
    ) -> None:
        super().__init__(coordinator, device)
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def unique_id(self):
        return super().unique_id + "_" + self._attr_name.replace(" ", "_")

    @property
    def min_temp(self) -> float:
        return self.device.range_control_temperature[0]

    @property
    def max_temp(self) -> float:
        return self.device.range_control_temperature[1]

    @property
    def current_temperature(self) -> float | None:
        return self.device.temperature

    @property
    def target_temperature(self) -> float | None:
        return self.device.target_temperature

    @property
    def temperature_unit(self) -> Optional[str]:
        if self.device.temperature_unit == TemperatureUnit.CELSIUS:
            return UnitOfTemperature.CELSIUS
        elif self.device.temperature_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        else:
            return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self.device.state == TRVState.HEATING:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    # Kasa seems to use Frost Protection to turn the TRV On and Off
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            (await self.device.set_frost_protection_off()).get_or_raise()
        else:
            (await self.device.set_frost_protection_on()).get_or_raise()

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        (await self.device.set_target_temp(kwargs)).get_or_raise()
        await self.coordinator.async_request_refresh()

