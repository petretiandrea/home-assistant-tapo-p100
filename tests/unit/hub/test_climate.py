from unittest.mock import AsyncMock, MagicMock
from unittest.mock import Mock

import pytest
from plugp100.common.functional.tri import Try
from plugp100.new.child.tapohubchildren import KE100Device

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.climate import TRVClimate
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
from plugp100.responses.hub_childs.ke100_device_state import TRVState
from plugp100.responses.temperature_unit import TemperatureUnit

from tests.conftest import _mock_hub_child_device


# class TestSensorMappings:
#     coordinator = Mock(TapoDataCoordinator)
#
#     def test_binary_sensor_mappings(self):
#         expected_mappings = {KE100Device: [TRVClimate]}
#
#         assert SENSOR_MAPPING == expected_mappings


class TestTRVClimate:

    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_hub_child_device(MagicMock(auto_spec=KE100Device))
        self.climate = TRVClimate(coordinator=self.coordinator, device=self.device)


    def test_unique_id(self):
        assert self.climate.unique_id == "123_Climate"

    def test_supported_features(self):
        assert self.climate.supported_features == ClimateEntityFeature.TARGET_TEMPERATURE

    def test_hvac_modes(self):
        assert self.climate.hvac_modes == [HVACMode.OFF, HVACMode.HEAT]

    def test_min_temp(self):
        self.device.range_control_temperature = [5.0, 30.0]
        assert self.climate.min_temp == 5.0

    def test_max_temp(self):
        self.device.range_control_temperature = [5.0, 30.0]
        assert self.climate.max_temp == 30.0

    def test_current_temperature(self):
        self.device.temperature = 20.1
        assert self.climate.current_temperature == 20.1

    def test_target_temperature(self):
        self.device.target_temperature = 22.0
        assert self.climate.target_temperature == 22.0

    @pytest.mark.parametrize(
        "trv_temperature_unit, expected_unit_of_temperature",
        [
            (TemperatureUnit.CELSIUS, UnitOfTemperature.CELSIUS),
            (TemperatureUnit.FAHRENHEIT, UnitOfTemperature.FAHRENHEIT),
        ],
    )
    def test_temperature_unit(
        self,
        trv_temperature_unit: TemperatureUnit,
        expected_unit_of_temperature: UnitOfTemperature,
    ):
        self.device.temperature_unit = trv_temperature_unit
        assert self.climate.temperature_unit == expected_unit_of_temperature

    @pytest.mark.parametrize(
        "trv_state, expected_hvac_mode",
        [(TRVState.HEATING, HVACMode.HEAT), (TRVState.OFF, HVACMode.OFF)],
    )
    def test_hvac_mode(self, trv_state: TRVState, expected_hvac_mode: HVACMode):
        self.device.state = trv_state
        assert self.climate.hvac_mode == expected_hvac_mode

    @pytest.mark.asyncio
    async def test_async_hvac_mode_heat(self):
        self.device.set_frost_protection_off = AsyncMock(return_value=Try.of(True))
        self.device.set_frost_protection_on = AsyncMock(return_value=Try.of(True))
        await self.climate.async_set_hvac_mode(HVACMode.HEAT)

        self.device.set_frost_protection_on.assert_not_called()
        self.device.set_frost_protection_off.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_hvac_mode_off(self):
        self.device.set_frost_protection_off = AsyncMock(return_value=Try.of(True))
        self.device.set_frost_protection_on = AsyncMock(return_value=Try.of(True))
        await self.climate.async_set_hvac_mode(HVACMode.OFF)

        self.device.set_frost_protection_off.assert_not_called()
        self.device.set_frost_protection_on.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_temperature(self):
        temp_args = {"temperature": 18}
        self.device.set_target_temp = AsyncMock(return_value=Try.of(True))
        await self.climate.async_set_temperature(**temp_args)
        self.device.set_target_temp.assert_called_once_with(temp_args)
