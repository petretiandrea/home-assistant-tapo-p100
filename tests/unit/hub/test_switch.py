from unittest.mock import AsyncMock, Mock, MagicMock, patch
import pytest

from custom_components.tapo.hub.switch import *

from custom_components.tapo.hub.tapo_hub_coordinator import TapoCoordinator

class TestSensorMappings:

    coordinator = Mock(TapoCoordinator)

    def test_binary_sensor_mappings(self):
        expected_mappings = \
        {
            SwitchChildDevice: [SwitchTapoChild],
            KE100Device: [TRVFrostProtection, TRVChildLock]
        }

        assert SWITCH_MAPPING == expected_mappings


class TestTRVFrostProtection:
    coordinator = Mock(TapoCoordinator)

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

        assert result == False

    def test_device_class(self):
        subject = TRVFrostProtection(coordinator=self.coordinator)

        result = subject.device_class

        assert result == SwitchDeviceClass.SWITCH

    @pytest.mark.asyncio
    async def test_async_turn_on(self):
        async_coordinator = AsyncMock(TapoCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVFrostProtection(coordinator=async_coordinator)

        await subject.async_turn_on()

        device.set_frost_protection_on.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_turn_off(self):
        async_coordinator = AsyncMock(TapoCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVFrostProtection(coordinator=async_coordinator)

        await subject.async_turn_off()

        device.set_frost_protection_off.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()


class TestTRVChildLock:
    coordinator = Mock(TapoCoordinator)

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

        assert result == True

    def test_device_class(self):
        subject = TRVChildLock(coordinator=self.coordinator)

        result = subject.device_class

        assert result == SwitchDeviceClass.SWITCH

    @pytest.mark.asyncio
    async def test_async_turn_on(self):
        async_coordinator = AsyncMock(TapoCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVChildLock(coordinator=async_coordinator)

        await subject.async_turn_on()

        device.set_child_protection_on.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_turn_off(self):
        async_coordinator = AsyncMock(TapoCoordinator)
        device = AsyncMock()
        async_coordinator.device = device

        subject = TRVChildLock(coordinator=async_coordinator)

        await subject.async_turn_off()

        device.set_child_protection_off.assert_called_once()
        async_coordinator.async_request_refresh.assert_called_once()