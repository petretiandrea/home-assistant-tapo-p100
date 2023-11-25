import pytest
from datetime import timedelta

from unittest.mock import Mock
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from plugp100.api.hub.hub_device import HubDevice
from plugp100.responses.hub_childs.hub_child_base_info import HubChildBaseInfo
from plugp100.api.hub.ke100_device import KE100Device
from plugp100.api.hub.s200b_device import S200ButtonDevice
from plugp100.api.hub.switch_child_device import SwitchChildDevice
from plugp100.api.hub.t100_device import T100MotionSensor
from plugp100.api.hub.t110_device import T110SmartDoor
from plugp100.api.hub.t31x_device import T31Device

from custom_components.tapo.hub.tapo_hub import TapoHub


class TestTapoHub:
    config = Mock(ConfigEntry)
    hub_device = Mock(HubDevice)
    hass = Mock(HomeAssistant)
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
            base_child_info = Mock(HubChildBaseInfo)
            base_child_info.model = model
            base_child_info.device_id = "123ABC"

            hub = TapoHub(entry=self.config, hub=self.hub_device)
            result = await hub.setup_child_coordinators(
                hass=self.hass,
                device_list=[base_child_info],
                polling_rate=self.polling_rate,
            )

            assert len(result) == 1
            assert type(result[0].device) == expected_type
            print(result[0].device)
