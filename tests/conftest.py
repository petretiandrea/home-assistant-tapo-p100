"""Global fixtures for tapo integration."""
import json
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import TapoDevice
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from plugp100.api.hub.hub_device import HubDevice
from plugp100.api.ledstrip_device import LedStripDevice
from plugp100.api.light_device import LightDevice
from plugp100.api.plug_device import PlugDevice
from plugp100.api.power_strip_device import PowerStripDevice
from plugp100.common.functional.tri import Success
from plugp100.common.functional.tri import Try
from plugp100.discovery.discovered_device import DiscoveredDevice
from plugp100.responses.alarm_type_list import AlarmTypeList
from plugp100.responses.child_device_list import ChildDeviceList
from plugp100.responses.child_device_list import PowerStripChild
from plugp100.responses.components import Components
from plugp100.responses.device_state import DeviceInfo
from plugp100.responses.device_state import HubDeviceState
from plugp100.responses.device_state import LedStripDeviceState
from plugp100.responses.device_state import LightDeviceState
from plugp100.responses.device_state import PlugDeviceState
from plugp100.responses.energy_info import EnergyInfo
from plugp100.responses.power_info import PowerInfo
from plugp100.responses.tapo_response import TapoResponse
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .tapo_mock_helper import tapo_response_child_of
from .tapo_mock_helper import tapo_response_of

pytest_plugins = ("pytest_homeassistant_custom_component",)

IP_ADDRESS = "1.2.3.4"
MAC_ADDRESS = "aa:bb:cc:dd:ee:ff"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    return True


@pytest.fixture()
def mock_discovery():
    (discovered_device, device_info) = mock_discovered_device()
    with patch(
        "custom_components.tapo.discovery_tapo_devices",
        AsyncMock(return_value={device_info.mac: device_info}),
    ):
        with patch(
            "custom_components.tapo.config_flow.TapoConfigFlow._async_get_device_info",
            AsyncMock(return_value=device_info),
        ):
            yield discovered_device


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
            CONF_HOST: IP_ADDRESS,
            CONF_USERNAME: "mock",
            CONF_PASSWORD: "mock",
            CONF_SCAN_INTERVAL: 5000,
        },
        version=8,
        unique_id=dr.format_mac(state.value.info.mac),
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


def mock_discovered_device() -> [DiscoveredDevice, DeviceInfo]:
    response = fixture_tapo_map("bulb.json")
    state = (
        response.get("get_device_info")
        .flat_map(lambda x: LightDeviceState.try_from_json(x.result))
        .get_or_raise()
        .info
    )
    return [
        DiscoveredDevice.from_dict(json.loads(load_fixture("discovery.json"))),
        state,
    ]


def mock_plug(with_emeter: bool = False) -> MagicMock:
    response = fixture_tapo_map("plug.json" if not with_emeter else "plug_emeter.json")
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

    if with_emeter:
        power = response.get("get_current_power").map(lambda x: PowerInfo(x.result))
        energy = response.get("get_energy_usage").map(lambda x: EnergyInfo(x.result))
        device.get_current_power = AsyncMock(return_value=power)
        device.get_energy_usage = AsyncMock(return_value=energy)

    device.device_id = state.value.info.device_id
    return device


def mock_hub(with_children: bool = False) -> MagicMock:
    response = fixture_tapo_map("hub.json")
    state = response.get("get_device_info").flat_map(
        lambda x: HubDeviceState.try_from_json(x.result)
    )
    components = response.get("component_nego").map(
        lambda x: Components.try_from_json(x.result)
    )
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
    if with_children:
        children = response.get("get_child_device_list").map(
            lambda x: ChildDeviceList.try_from_json(**x.result)
        )
        device.get_children = AsyncMock(return_value=children)
    device.__class__ = HubDevice
    device.device_id = state.value.info.device_id
    return device


def mock_bulb(components_to_exclude: list[str] = []) -> MagicMock:
    response = fixture_tapo_map("bulb.json")
    state = response.get("get_device_info").flat_map(
        lambda x: LightDeviceState.try_from_json(x.result)
    )
    components = (
        response.get("component_nego")
        .map(lambda x: Components.try_from_json(x.result))
        .map(lambda x: exclude_components(x, components_to_exclude))
    )
    device = MagicMock(auto_spec=LightDevice, name="Mocked bulb device")
    device.on = AsyncMock(return_value=Success(True))
    device.off = AsyncMock(return_value=Success(True))
    device.set_brightness = AsyncMock(return_value=Success(True))
    device.set_hue_saturation = AsyncMock(return_value=Success(True))
    device.set_color_temperature = AsyncMock(return_value=Success(True))
    device.get_state = AsyncMock(return_value=state)
    device.get_component_negotiation = AsyncMock(return_value=components)
    device.__class__ = LightDevice

    device.device_id = state.value.info.device_id
    return device


def mock_led_strip() -> MagicMock:
    response = fixture_tapo_map("ledstrip.json")
    state = response.get("get_device_info").flat_map(
        lambda x: LedStripDeviceState.try_from_json(x.result)
    )
    components = response.get("component_nego").map(
        lambda x: Components.try_from_json(x.result)
    )
    device = MagicMock(auto_spec=LedStripDevice, name="Mocked led strip device")
    device.on = AsyncMock(return_value=Success(True))
    device.off = AsyncMock(return_value=Success(True))
    device.set_brightness = AsyncMock(return_value=Success(True))
    device.set_hue_saturation = AsyncMock(return_value=Success(True))
    device.set_color_temperature = AsyncMock(return_value=Success(True))
    device.set_light_effect = AsyncMock(return_value=Success(True))
    device.set_light_effect_brightness = AsyncMock(return_value=Success(True))
    device.get_state = AsyncMock(return_value=state)
    device.get_component_negotiation = AsyncMock(return_value=components)
    device.__class__ = LedStripDevice
    device.device_id = state.value.info.device_id
    return device


async def extract_entity_id(device: TapoDevice, platform: str, postfix: str = ""):
    nickname = (
        (await device.get_state())
        .map(lambda x: x.info.nickname if x.info.nickname != "" else x.info.model)
        .get_or_raise()
    )

    return platform + "." + (nickname + " " + postfix).strip().lower().replace(" ", "_")


def exclude_components(components: Components, to_exclude: list[str]) -> Components:
    component_list = {
        "component_list": [
            {"id": component, "ver_code": components.get_version(component)}
            for component in filter(
                lambda x: x not in to_exclude, components.component_list
            )
        ]
    }
    return Components.try_from_json(component_list)


def mock_plug_strip() -> MagicMock:
    response = fixture_tapo_map("plug_strip.json")
    state = response.get("get_device_info").flat_map(
        lambda x: PlugDeviceState.try_from_json(x.result)
    )
    components = response.get("component_nego").map(
        lambda x: Components.try_from_json(x.result)
    )
    device = MagicMock(auto_spec=PowerStripDevice, name="Mocked plug strip device")
    device.get_state = AsyncMock(return_value=state)
    device.get_component_negotiation = AsyncMock(return_value=components)
    device.on = AsyncMock(return_value=Success(True))
    device.off = AsyncMock(return_value=Success(True))
    children = (
        response.get("get_child_device_list")
        .map(lambda x: ChildDeviceList.try_from_json(**x.result))
        .map(lambda sub: sub.get_children(lambda x: PowerStripChild.try_from_json(**x)))
        .map(lambda x: {child.device_id: child for child in x})
    )
    device.get_children = AsyncMock(return_value=children)
    device.__class__ = PowerStripDevice
    device.device_id = state.value.info.device_id

    return device
