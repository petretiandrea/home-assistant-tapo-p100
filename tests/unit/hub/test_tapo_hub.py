from datetime import timedelta
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from custom_components.tapo.hub.tapo_hub import TapoHub
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device
from plugp100.responses.hub_childs.hub_child_base_info import HubChildBaseInfo


class TestTapoHub:
    config = Mock(ConfigEntry)
    hub_device = Mock(HubDevice)
    hass = Mock(HomeAssistant)
    registry = Mock(DeviceRegistry)
    polling_rate = Mock(timedelta)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model, expected_type",
        [
            ("KE100", KE100Device),
            ("T31", T31Device),
            ("T110", T110SmartDoor),
            ("S200", S200ButtonDevice),
            ("T100", T100MotionSensor),
            ("S220", SwitchChildDevice),
            ("S210", SwitchChildDevice),
        ],
    )
    async def test_setup_child_coordinators_should_create_correct_types(
        self, model: str, expected_type: type
    ):
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            with patch(
                "homeassistant.helpers.device_registry.DeviceRegistry.async_get_or_create"
            ):
                with patch(
                    "homeassistant.helpers.device_registry.async_entries_for_config_entry"
                ):
                    base_child_info = Mock(HubChildBaseInfo)
                    base_child_info.model = model
                    base_child_info.device_id = "123ABC"
                    base_child_info.nickname = "123ABC"
                    base_child_info.firmware_version = "1.2.3"
                    base_child_info.hardware_version = "hw1.0"

                    hub = TapoHub(entry=self.config, hub=self.hub_device)
                    result = await hub.setup_children(
                        hass=self.hass,
                        registry=self.registry,
                        device_list=[base_child_info],
                        polling_rate=self.polling_rate,
                    )

                    assert len(result) == 1
                    assert result[0].device is expected_type
                    print(result[0].device)

    @pytest.mark.asyncio
    async def test_setup_all_children(self):
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            with patch(
                "homeassistant.helpers.device_registry.DeviceRegistry.async_get_or_create"
            ):
                with patch(
                    "homeassistant.helpers.device_registry.async_entries_for_config_entry"
                ):
                    children = []
                    for i in range(0, 100):
                        mock = Mock(HubChildBaseInfo)
                        mock.model = "T110"
                        mock.device_id = f"123ABC{i}"
                        mock.nickname = f"123ABC{i}"
                        mock.firmware_version = f"1.2.{i}"
                        mock.hardware_version = f"hw{i}.0"
                        children.append(mock)

                    hub = TapoHub(entry=self.config, hub=self.hub_device)
                    result = await hub.setup_children(
                        hass=self.hass,
                        registry=self.registry,
                        device_list=children,
                        polling_rate=self.polling_rate,
                    )

                    assert len(result) == 100
