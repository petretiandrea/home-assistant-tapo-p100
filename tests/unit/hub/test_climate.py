from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.climate import SENSOR_MAPPING
from custom_components.tapo.hub.climate import TRVClimate
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.responses.hub_childs.ke100_device_state import TRVState
from plugp100.responses.temperature_unit import TemperatureUnit


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_binary_sensor_mappings(self):
        expected_mappings = {KE100Device: [TRVClimate]}

        assert SENSOR_MAPPING == expected_mappings


class TestTRVClimate:
    coordinator = Mock(TapoDataCoordinator)

    def test_unique_id(self):
        base_data = Mock()
        base_data.base_info.device_id = "hub1234"
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.unique_id

        assert result == "hub1234_Climate"

    def test_supported_features(self):
        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.supported_features

        assert result == ClimateEntityFeature.TARGET_TEMPERATURE

    def test_hvac_modes(self):
        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.hvac_modes

        assert result == [HVACMode.OFF, HVACMode.HEAT]

    def test_min_temp(self):
        base_data = Mock()
        base_data.min_control_temperature = 5.0
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.min_temp

        assert result == 5.0

    def test_max_temp(self):
        base_data = Mock()
        base_data.max_control_temperature = 30.0
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.max_temp

        assert result == 30.0

    def test_current_temperature(self):
        base_data = Mock()
        base_data.current_temperature = 20.1
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.current_temperature

        assert result == 20.1

    def test_target_temperature(self):
        base_data = Mock()
        base_data.target_temperature = 22.0
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.target_temperature

        assert result == 22.0

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
        base_data = Mock()
        base_data.temperature_unit = trv_temperature_unit
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.temperature_unit

        assert result == expected_unit_of_temperature

    @pytest.mark.parametrize(
        "trv_state, expected_hvac_mode",
        [(TRVState.HEATING, HVACMode.HEAT), (TRVState.OFF, HVACMode.OFF)],
    )
    def test_hvac_mode(self, trv_state: TRVState, expected_hvac_mode: HVACMode):
        base_data = Mock()
        base_data.trv_state = trv_state
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVClimate(coordinator=self.coordinator)

        result = subject.hvac_mode

        assert result == expected_hvac_mode

    @pytest.mark.asyncio
    async def test_async_hvac_mode_heat(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVClimate(coordinator=async_coordinator)

        await subject.async_set_hvac_mode(HVACMode.HEAT)

        device.set_frost_protection_on.set_frost_protection_off()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_hvac_mode_off(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVClimate(coordinator=async_coordinator)

        await subject.async_set_hvac_mode(HVACMode.OFF)

        device.set_frost_protection_on.set_frost_protection_on()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_temperature(self):
        temp_args = {"temperature": 18}
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVClimate(coordinator=async_coordinator)

        await subject.async_set_temperature(**temp_args)

        device.set_target_temp.assert_called_once_with(temp_args)
        async_coordinator.async_request_refresh.assert_called_once()
