from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildCommonState
from custom_components.tapo.hub.tapo_hub_child_coordinator import HubChildDevice
from custom_components.tapo.hub.tapo_hub_child_coordinator import (
    TapoHubChildCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.ke100_device import KE100DeviceState
from plugp100.api.hub.s200b_device import S200BDeviceState
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.switch_child_device import SwitchChildDeviceState
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t100_device import T100MotionSensorState
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t110_device import T110SmartDoorState
from plugp100.api.hub.t31x_device import T31Device
from plugp100.api.hub.t31x_device import T31DeviceState
from plugp100.api.hub.water_leak_device import LeakDeviceState
from plugp100.api.hub.water_leak_device import WaterLeakSensor
from plugp100.common.functional.tri import Try


class TestTapoHubChildCoordinator:
    config = Mock(ConfigEntry)
    hass = Mock(HomeAssistant)
    polling_rate = Mock(timedelta)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "device_type, expected_device_state, expected_nickname",
        [
            (KE100Device, Mock(KE100DeviceState), "ke100"),
            (T110SmartDoor, Mock(T110SmartDoorState), "t110"),
            (WaterLeakSensor, Mock(LeakDeviceState), "leaky"),
            (T100MotionSensor, Mock(T100MotionSensorState), "t100"),
        ],
    )
    async def test_setup_child_coordinators_should_create_correct_types(
        self,
        device_type: HubChildDevice,
        expected_device_state: HubChildCommonState,
        expected_nickname: str,
    ):
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            device = AsyncMock(device_type)

            device.get_device_state.return_value = Try.of(expected_device_state)
            expected_device_state.return_value.nickname = expected_nickname

            hub_child_coordinator = TapoHubChildCoordinator(
                hass=self.hass, device=device, polling_interval=self.polling_rate
            )
            await hub_child_coordinator._update_state()

            state_values = list(hub_child_coordinator._states.values())

            assert len(state_values) == 1
            assert state_values[0].nickname == expected_nickname

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "device_type, expected_device_state, expected_nickname",
        [
            (S200ButtonDevice, Mock(S200BDeviceState), "s200"),
            (SwitchChildDevice, Mock(SwitchChildDeviceState), "s220"),
            (SwitchChildDevice, Mock(SwitchChildDeviceState), "s210"),
        ],
    )
    async def test_setup_child_coordinators_should_create_correct_types_get_device_info(
        self,
        device_type: HubChildDevice,
        expected_device_state: HubChildCommonState,
        expected_nickname: str,
    ):
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            device = AsyncMock(device_type)

            device.get_device_info.return_value = Try.of(expected_device_state)
            expected_device_state.return_value.nickname = expected_nickname

            hub_child_coordinator = TapoHubChildCoordinator(
                hass=self.hass, device=device, polling_interval=self.polling_rate
            )
            await hub_child_coordinator._update_state()

            state_values = list(hub_child_coordinator._states.values())

            assert len(state_values) == 1
            assert state_values[0].nickname == expected_nickname

    @pytest.mark.asyncio
    async def test_setup_child_coordinators_t31_device(self):
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            device = AsyncMock(T31Device)
            expected_device_state = Mock(T31DeviceState)
            expected_nickname = "t31"

            device.get_device_state.return_value = Try.of(expected_device_state)
            expected_device_state.return_value.nickname = expected_nickname

            hub_child_coordinator = TapoHubChildCoordinator(
                hass=self.hass, device=device, polling_interval=self.polling_rate
            )
            await hub_child_coordinator._update_state()

            state_values = list(hub_child_coordinator._states.values())

            assert len(state_values) == 2
            assert state_values[0].nickname == expected_nickname
            device.get_temperature_humidity_records.assert_called_once()
