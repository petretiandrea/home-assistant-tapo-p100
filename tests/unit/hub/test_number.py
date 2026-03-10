from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from plugp100.common.functional.tri import Try
from plugp100.new.child.tapohubchildren import KE100Device, TriggerButtonDevice
from plugp100.responses.temperature_unit import TemperatureUnit

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.number import (
    DEFAULT_POLL_UTILIZATION,
    PollUtilization,
    TRVTemperatureOffset,
)
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


class TestPollUtilization:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_hub_child_device(MagicMock(auto_spec=TriggerButtonDevice))
        self.entity = PollUtilization(
            coordinator=self.coordinator, device=self.device
        )

    def test_unique_id(self):
        assert self.entity.unique_id == "123_poll_utilization"

    def test_name(self):
        assert self.entity._attr_name == "Poll Utilization"

    def test_entity_category(self):
        assert self.entity._attr_entity_category == EntityCategory.CONFIG

    def test_icon(self):
        assert self.entity._attr_icon == "mdi:speedometer"

    def test_min_value(self):
        assert self.entity._attr_native_min_value == 5

    def test_max_value(self):
        assert self.entity._attr_native_max_value == 50

    def test_step(self):
        assert self.entity._attr_native_step == 5

    def test_mode(self):
        assert self.entity._attr_mode == NumberMode.SLIDER

    def test_unit_of_measurement(self):
        assert self.entity._attr_native_unit_of_measurement == PERCENTAGE

    def test_default_value(self):
        assert self.entity._attr_native_value == float(DEFAULT_POLL_UTILIZATION)

    async def test_async_set_native_value_updates_entity(self):
        self.entity.async_write_ha_state = MagicMock()
        await self.entity.async_set_native_value(20.0)
        assert self.entity._attr_native_value == 20.0

    async def test_async_set_native_value_stores_on_coordinator(self):
        self.entity.async_write_ha_state = MagicMock()
        await self.entity.async_set_native_value(25.0)
        assert self.coordinator._poll_utilization_pct == 25.0

    async def test_async_set_native_value_calls_write_ha_state(self):
        self.entity.async_write_ha_state = MagicMock()
        await self.entity.async_set_native_value(30.0)
        self.entity.async_write_ha_state.assert_called_once()

    async def test_async_added_to_hass_sets_coordinator_pct(self):
        self.entity.hass = MagicMock()
        self.entity.platform = MagicMock()
        # Mock RestoreNumber's async_get_last_number_data to return None
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                self.entity, "async_get_last_number_data",
                AsyncMock(return_value=None)
            )
            # Mock super().async_added_to_hass
            with pytest.MonkeyPatch.context() as m2:
                m2.setattr(
                    PollUtilization.__bases__[1], "async_added_to_hass",
                    AsyncMock(return_value=None)
                )
                await self.entity.async_added_to_hass()
        assert self.coordinator._poll_utilization_pct == float(DEFAULT_POLL_UTILIZATION)
