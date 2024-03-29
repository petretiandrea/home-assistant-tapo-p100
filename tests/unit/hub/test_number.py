from unittest.mock import MagicMock, AsyncMock
from unittest.mock import Mock

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number import NumberMode
from homeassistant.const import UnitOfTemperature
from plugp100.common.functional.tri import Try
from plugp100.new.child.tapohubchildren import KE100Device
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.number import TRVTemperatureOffset
from tests.conftest import _mock_hub_child_device


# class TestSensorMappings:
#     coordinator = Mock(TapoDataCoordinator)
#
#     def test_binary_sensor_mappings(self):
#         expected_mappings = {KE100Device: [TRVTemperatureOffset]}
#
#         assert SENSOR_MAPPING == expected_mappings


class TestTRVTemperatureOffset:

    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_hub_child_device(MagicMock(auto_spec=KE100Device))
        self.temperature_offset = TRVTemperatureOffset(coordinator=self.coordinator, device=self.device)

    async def test_unique_id(self):
        assert self.temperature_offset.unique_id == "123_Temperature_Offset"

    async def test_device_class(self):
        assert self.temperature_offset.device_class == NumberDeviceClass.TEMPERATURE

    async def test_native_min_value(self):
        assert self.temperature_offset.native_min_value == -10

    async def test_native_max_value(self):
        assert self.temperature_offset.native_max_value == 10

    async def test_mode(self):
        assert self.temperature_offset.mode == NumberMode.AUTO

    async def test_native_step(self):
        assert self.temperature_offset.native_step == 1

    async def test_native_value(self):
        self.device.temperature_offset = -4
        assert self.temperature_offset.native_value == -4

    @pytest.mark.parametrize(
        "temperature_unit, expected_unit_of_temperature",
        [
            (TemperatureUnit.CELSIUS, UnitOfTemperature.CELSIUS),
            (TemperatureUnit.FAHRENHEIT, UnitOfTemperature.FAHRENHEIT),
        ],
    )
    async def test_native_unit_of_measurement(
        self,
        temperature_unit: TemperatureUnit,
        expected_unit_of_temperature: UnitOfTemperature,
    ):
        self.device.temperature_unit = temperature_unit
        assert self.temperature_offset.native_unit_of_measurement == expected_unit_of_temperature


    async def test_async_set_native_value(self):
        value = 8
        self.device.set_temp_offset = AsyncMock(return_value=Try.of(True))
        await self.temperature_offset.async_set_native_value(value=value)
        self.device.set_temp_offset.assert_called_once_with(value)
