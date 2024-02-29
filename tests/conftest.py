"""Global fixtures for tapo integration."""
import json
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import TapoDevice
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.plug_device import PlugDevice
from plugp100.common.functional.tri import Success
from plugp100.common.functional.tri import Try
from plugp100.responses.alarm_type_list import AlarmTypeList
from plugp100.responses.child_device_list import ChildDeviceList
from plugp100.responses.components import Components
from plugp100.responses.device_state import HubDeviceState
from plugp100.responses.device_state import PlugDeviceState
from plugp100.responses.tapo_response import TapoResponse
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .tapo_mock_helper import tapo_response_child_of
from .tapo_mock_helper import tapo_response_of

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    return True


def fixture_tapo_map(resource: str) -> dict[str, Try[TapoResponse]]:
    elems = json.loads(load_fixture(resource))
    return {k: tapo_response_of(elems[k]) for k in elems.keys()}


def fixture_tapo_response(resource: str) -> Try[TapoResponse]:
    return tapo_response_of(json.loads(load_fixture(resource)))


def fixture_tapo_response_child(resource: str) -> Try[TapoResponse]:
    return tapo_response_child_of(json.loads(load_fixture(resource)))


async def setup_platform(
    hass: HomeAssistant, device: TapoDevice, platforms: list[str]
) -> MockConfigEntry:
    hass.config.components.add(DOMAIN)
    state = await device.get_state()
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.2.3.4",
            CONF_USERNAME: "mock",
            CONF_PASSWORD: "mock",
            CONF_SCAN_INTERVAL: 5000,
            CONF_TRACK_DEVICE: False,
        },
        version=6,
        unique_id=state.value.info.device_id,
    )
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.tapo.hass_tapo.HassTapo._get_initial_device_state",
        return_value=state.value.info,
    ):
        with patch(
            "custom_components.tapo.hass_tapo.create_tapo_device", return_value=device
        ):
            with patch.object(hass.config_entries, "async_forward_entry_setup"):
                assert (
                    await hass.config_entries.async_setup(config_entry.entry_id) is True
                )
                assert await async_setup_component(hass, DOMAIN, {}) is True
                await hass.async_block_till_done()

    for platform in platforms:
        assert await hass.config_entries.async_forward_entry_setup(
            config_entry, platform
        )
    await hass.async_block_till_done()

    return config_entry


def mock_switch() -> MagicMock:
    response = fixture_tapo_map("plug_p105.json")
    state = response.get("get_device_info").flat_map(
        lambda x: PlugDeviceState.try_from_json(x.result)
    )
    components = response.get("component_nego").map(
        lambda x: Components.try_from_json(x.result)
    )
    device = MagicMock(auto_spec=PlugDevice, name="Mocked plug device")
    device.on = AsyncMock(return_value=Success(True))
    device.off = AsyncMock(return_value=Success(True))
    device.get_state = AsyncMock(return_value=state)
    device.get_component_negotiation = AsyncMock(return_value=components)
    device.__class__ = PlugDevice
    return device


def mock_hub() -> MagicMock:
    response = fixture_tapo_map("hub.json")
    state = response.get("get_device_info").flat_map(
        lambda x: HubDeviceState.try_from_json(x.result)
    )
    components = response.get("component_nego").map(
        lambda x: Components.try_from_json(x.result)
    )
    # children = response.get("get_child_device_list").map(
    #     lambda x: ChildDeviceList.try_from_json(**x.result)
    # )

    device = MagicMock(auto_spec=HubDevice, name="Mocked hub device")
    device.turn_alarm_on = AsyncMock(return_value=Success(True))
    device.turn_alarm_off = AsyncMock(return_value=Success(True))
    device.get_state = AsyncMock(return_value=state)
    device.get_component_negotiation = AsyncMock(return_value=components)
    device.get_children = AsyncMock(return_value=Success(ChildDeviceList([], 0, 0)))
    device.subscribe_device_association = MagicMock()
    device.get_supported_alarm_tones = AsyncMock(
        return_value=Success(AlarmTypeList(["test_tone"]))
    )
    device.__class__ = HubDevice
    return device
