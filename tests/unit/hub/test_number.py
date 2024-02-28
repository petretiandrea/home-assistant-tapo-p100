from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.number import SENSOR_MAPPING
from custom_components.tapo.hub.number import TRVTemperatureOffset
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number import NumberMode
from homeassistant.const import UnitOfTemperature
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.responses.temperature_unit import TemperatureUnit


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_binary_sensor_mappings(self):
        expected_mappings = {KE100Device: [TRVTemperatureOffset]}

        assert SENSOR_MAPPING == expected_mappings


class TestTRVTemperatureOffset:
    coordinator = Mock(TapoDataCoordinator)

    def test_unique_id(self):
        base_data = Mock()
        base_data.base_info.device_id = "hub1234"
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.unique_id

        assert result == "hub1234_Temperature_Offset"

    def test_device_class(self):
        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.device_class

        assert result == NumberDeviceClass.TEMPERATURE

    def test_native_min_value(self):
        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.native_min_value

        assert result == -10

    def test_native_max_value(self):
        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.native_max_value

        assert result == 10

    def test_mode(self):
        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.mode

        assert result == NumberMode.AUTO

    def test_native_step(self):
        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.native_step

        assert result == 1

    def test_native_value(self):
        base_data = Mock()
        base_data.temperature_offset = -4
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.native_value

        assert result == -4

    @pytest.mark.parametrize(
        "temperature_unit, expected_unit_of_temperature",
        [
            (TemperatureUnit.CELSIUS, UnitOfTemperature.CELSIUS),
            (TemperatureUnit.FAHRENHEIT, UnitOfTemperature.FAHRENHEIT),
        ],
    )
    def test_native_unit_of_measurement(
        self,
        temperature_unit: TemperatureUnit,
        expected_unit_of_temperature: UnitOfTemperature,
    ):
        base_data = Mock()
        base_data.temperature_unit = temperature_unit
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVTemperatureOffset(coordinator=self.coordinator)

        result = subject.native_unit_of_measurement

        assert result == expected_unit_of_temperature

    @pytest.mark.asyncio
    async def test_async_set_native_value(self):
        value = 8
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVTemperatureOffset(coordinator=async_coordinator)

        await subject.async_set_native_value(value=value)

        device.set_temp_offset.assert_called_once_with(value)
        async_coordinator.async_request_refresh.assert_called_once()
