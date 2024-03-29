from unittest.mock import AsyncMock, MagicMock
from unittest.mock import Mock

import pytest
from homeassistant.components.switch import SwitchDeviceClass
from plugp100.common.functional.tri import Try
from plugp100.new.child.tapohubchildren import KE100Device

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.switch import TRVChildLock
from custom_components.tapo.hub.switch import TRVFrostProtection
from tests.conftest import _mock_hub_child_device


# TODO: convert to try setup config entry
# class TestSensorMappings:
#     coordinator = Mock(TapoDataCoordinator)
#
#     def test_binary_sensor_mappings(self):
#         expected_mappings = {
#             SwitchChildDevice: [SwitchTapoChild],
#             KE100Device: [TRVFrostProtection, TRVChildLock],
#         }
#
#         assert SWITCH_MAPPING == expected_mappings


class TestTRVFrostProtection:

    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_hub_child_device(MagicMock(auto_spec=KE100Device))
        self.frost_protection = TRVFrostProtection(coordinator=self.coordinator, device=self.device)

    async def test_unique_id(self):
        assert self.frost_protection.unique_id == "123_Frost_Protection"

    async def test_is_on(self):
        assert self.frost_protection.is_on is False

    async def test_device_class(self):
        assert self.frost_protection.device_class == SwitchDeviceClass.SWITCH

    async def test_async_turn_on(self):
        self.device.set_frost_protection_on = AsyncMock(return_value=Try.of(True))
        await self.frost_protection.async_turn_on()
        self.device.set_frost_protection_on.assert_called_once()

    async def test_async_turn_off(self):
        self.device.set_frost_protection_off = AsyncMock(return_value=Try.of(True))
        await self.frost_protection.async_turn_off()
        self.device.set_frost_protection_off.assert_called_once()


class TestTRVChildLock:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device = _mock_hub_child_device(MagicMock(auto_spec=KE100Device))
        self.child_lock = TRVChildLock(coordinator=self.coordinator, device=self.device)

    async def test_unique_id(self):
        assert self.child_lock.unique_id == "123_Child_Lock"

    def test_is_on(self):
        self.device.is_child_protection_on = True
        assert self.child_lock.is_on is True

    def test_device_class(self):
        assert self.child_lock.device_class == SwitchDeviceClass.SWITCH

    async def test_async_turn_on(self):
        self.device.set_child_protection_on = AsyncMock(return_value=Try.of(True))
        await self.child_lock.async_turn_on()
        self.device.set_child_protection_on.assert_called_once()

    async def test_async_turn_off(self):
        self.device.set_child_protection_off = AsyncMock(return_value=Try.of(True))
        await self.child_lock.async_turn_off()
        self.device.set_child_protection_off.assert_called_once()
