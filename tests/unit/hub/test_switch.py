from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.switch import SWITCH_MAPPING
from custom_components.tapo.hub.switch import SwitchTapoChild
from custom_components.tapo.hub.switch import TRVChildLock
from custom_components.tapo.hub.switch import TRVFrostProtection
from homeassistant.components.switch import SwitchDeviceClass
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.switch_child_device import SwitchChildDevice


class TestSensorMappings:
    coordinator = Mock(TapoDataCoordinator)

    def test_binary_sensor_mappings(self):
        expected_mappings = {
            SwitchChildDevice: [SwitchTapoChild],
            KE100Device: [TRVFrostProtection, TRVChildLock],
        }

        assert SWITCH_MAPPING == expected_mappings


class TestTRVFrostProtection:
    coordinator = Mock(TapoDataCoordinator)

    def test_unique_id(self):
        base_data = Mock()
        base_data.base_info.device_id = "hub1234"
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVFrostProtection(coordinator=self.coordinator)

        result = subject.unique_id

        assert result == "hub1234_Frost_Protection"

    def test_is_on(self):
        base_data = Mock()
        base_data.frost_protection_on = False
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVFrostProtection(coordinator=self.coordinator)

        result = subject.is_on

        assert result is False

    def test_device_class(self):
        subject = TRVFrostProtection(coordinator=self.coordinator)

        result = subject.device_class

        assert result == SwitchDeviceClass.SWITCH

    @pytest.mark.asyncio
    async def test_async_turn_on(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVFrostProtection(coordinator=async_coordinator)

        await subject.async_turn_on()

        device.set_frost_protection_on.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_turn_off(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVFrostProtection(coordinator=async_coordinator)

        await subject.async_turn_off()

        device.set_frost_protection_off.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()


class TestTRVChildLock:
    coordinator = Mock(TapoDataCoordinator)

    def test_unique_id(self):
        base_data = Mock()
        base_data.base_info.device_id = "hub1234"
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVChildLock(coordinator=self.coordinator)

        result = subject.unique_id

        assert result == "hub1234_Child_Lock"

    def test_is_on(self):
        base_data = Mock()
        base_data.child_protection = True
        self.coordinator.get_state_of.return_value = base_data

        subject = TRVChildLock(coordinator=self.coordinator)

        result = subject.is_on

        assert result is True

    def test_device_class(self):
        subject = TRVChildLock(coordinator=self.coordinator)

        result = subject.device_class

        assert result == SwitchDeviceClass.SWITCH

    @pytest.mark.asyncio
    async def test_async_turn_on(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVChildLock(coordinator=async_coordinator)

        await subject.async_turn_on()

        device.set_child_protection_on.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_turn_off(self):
        async_coordinator = AsyncMock(TapoDataCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVChildLock(coordinator=async_coordinator)

        await subject.async_turn_off()

        device.set_child_protection_off.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()
