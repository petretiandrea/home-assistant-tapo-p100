"""Global fixtures for tapo integration."""
import json
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from plugp100.api.light_effect_preset import LightEffectPreset
from plugp100.common.functional.tri import Success
from plugp100.common.functional.tri import Try
from plugp100.discovery.discovered_device import DiscoveredDevice
from plugp100.new.child.tapostripsocket import TapoStripSocket
from plugp100.new.components.energy_component import EnergyComponent
from plugp100.new.components.light_component import HS, LightComponent
from plugp100.new.components.light_effect_component import LightEffectComponent
from plugp100.new.components.overheat_component import OverheatComponent
from plugp100.new.tapobulb import TapoBulb
from plugp100.new.tapodevice import TapoDevice
from plugp100.new.tapohub import TapoHub
from plugp100.new.tapoplug import TapoPlug
from plugp100.responses.alarm_type_list import AlarmTypeList
from plugp100.responses.components import Components
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DOMAIN

pytest_plugins = ("pytest_homeassistant_custom_component",)

IP_ADDRESS = "1.2.3.4"
MAC_ADDRESS = "1a:22:33:b4:c5:66"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    return True


@pytest.fixture()
def mock_discovery():
    discovered_device = mock_discovered_device()
    device = _mock_base_device(MagicMock(auto_spec=TapoDevice))
    with patch(
        "custom_components.tapo.discovery_tapo_devices",
        AsyncMock(return_value={device.mac: discovered_device}),
    ):
        with patch.object(
            discovered_device,
            "get_tapo_device",
            side_effect=AsyncMock(return_value=device),
        ):
            with patch("plugp100.discovery.discovered_device.DiscoveredDevice.get_tapo_device", side_effect=AsyncMock(return_value=device)):
                yield discovered_device

async def setup_platform(
    hass: HomeAssistant, device: TapoDevice, platforms: list[str]
) -> MockConfigEntry:
    hass.config.components.add(DOMAIN)
    await device.update()
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: IP_ADDRESS,
            CONF_USERNAME: "mock",
            CONF_PASSWORD: "mock",
            CONF_SCAN_INTERVAL: 5000,
        },
        version=8,
        unique_id=dr.format_mac(device.mac),
    )
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.tapo.hass_tapo.connect", AsyncMock(return_value=device)
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


def mock_discovered_device() -> DiscoveredDevice:
    return DiscoveredDevice.from_dict(json.loads(load_fixture("discovery.json")))

def mock_plug(with_emeter: bool = False) -> MagicMock:
    device = _mock_base_device(MagicMock(auto_spec=TapoPlug, name="Mocked plug device"))
    device.turn_on = AsyncMock(return_value=Success(True))
    device.turn_off = AsyncMock(return_value=Success(True))
    device.is_on = True
    device.is_strip = False
    device.model = "P100"
    device.__class__ = TapoPlug

    if with_emeter:
        emeter = MagicMock(EnergyComponent(MagicMock()))
        emeter.update = AsyncMock(return_value=None)
        emeter.energy_info.today_runtime = 3
        emeter.energy_info.month_runtime = 19742
        emeter.energy_info.today_energy = 0
        emeter.energy_info.month_energy = 1421
        emeter.energy_info.current_power = 1.2
        emeter.power_info = None
        device.add_component(emeter)

    return device


def mock_hub(with_children: bool = False) -> MagicMock:
    device = _mock_base_device(MagicMock(auto_spec=TapoHub, name="Mocked hub device"))
    device.turn_alarm_on = AsyncMock(return_value=Success(True))
    device.turn_alarm_off = AsyncMock(return_value=Success(True))
    device.has_alarm = True
    device.is_alarm_on = True
    device.subscribe_device_association = MagicMock()
    device.get_supported_alarm_tones = AsyncMock(
        return_value=Success(AlarmTypeList(["test_tone"]))
    )
    device.children = []
    device.__class__ = TapoHub
    return device


def mock_bulb(is_color: bool = True) -> MagicMock:
    device = _mock_base_device(MagicMock(TapoBulb("", 80, MagicMock()), name="Mocked bulb device"))
    device.is_color = is_color
    device.is_color_temperature = True
    device.is_led_strip = False
    device.device_on = True
    device.brightness = 100
    device.hs = HS(139, 38)
    device.color_temp = 6493
    device.color_temp_range = [2500, 6500]
    device.effect = None
    device.turn_on = AsyncMock(return_value=Try.of(True))
    device.turn_off = AsyncMock(return_value=Try.of(True))
    device.set_brightness = AsyncMock(return_value=Try.of(True))
    device.set_hue_saturation = AsyncMock(return_value=Try.of(True))
    device.set_color_temperature = AsyncMock(return_value=Try.of(True))
    device.set_light_effect = AsyncMock(return_value=Try.of(True))
    device.set_light_effect_brightness = AsyncMock(return_value=Try.of(True))
    device.__class__ = TapoBulb

    return device


def mock_led_strip() -> MagicMock:
    device = _mock_base_device(MagicMock(auto_spec=TapoBulb, name="Mocked led strip device"))
    device.is_color = True
    device.is_color_temperature = True
    device.is_led_strip = True
    device.device_on = True
    device.brightness = 100
    device.hs = HS(139, 38)
    device.color_temp = 6493
    device.color_temp_range = [2500, 6500]
    device.effect = LightEffectPreset.Ocean.to_effect()
    device.turn_on = AsyncMock(return_value=Try.of(True))
    device.turn_off = AsyncMock(return_value=Try.of(True))
    device.set_brightness = AsyncMock(return_value=Try.of(True))
    device.set_hue_saturation = AsyncMock(return_value=Try.of(True))
    device.set_color_temperature = AsyncMock(return_value=Try.of(True))
    device.set_light_effect = AsyncMock(return_value=Try.of(True))
    device.set_light_effect_brightness = AsyncMock(return_value=Try.of(True))
    device.__class__ = TapoBulb

    light_component = MagicMock(LightComponent(MagicMock()), name="Light component")
    light_component.update = AsyncMock(return_value=None)
    effect_component = MagicMock(LightEffectComponent(MagicMock()), name = "Light effect component")
    effect_component.update = AsyncMock(return_value=None)
    device.add_component(light_component)
    device.add_component(effect_component)
    return device


def _mock_overheat(device) -> MagicMock:
    overheat = MagicMock(OverheatComponent())
    overheat.update = AsyncMock(return_value=None)
    overheat.overheated = False
    device.add_component(overheat)
    return device

async def extract_entity_id(device: TapoDevice, platform: str, postfix: str = ""):
    nickname = device.nickname
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
    device = _mock_base_device(MagicMock(auto_spec=TapoPlug, name="Mocked plug strip device"))
    device.turn_on = AsyncMock(return_value=Success(True))
    device.turn_off = AsyncMock(return_value=Success(True))
    device.is_on = True
    device.is_strip = True
    device.model = "P300"
    device.__class__ = TapoPlug
    _mock_overheat(device)

    sockets = []
    for i in range(0, 3):
        sock = _mock_base_device(MagicMock(auto_spec=TapoStripSocket, name=f"Mocked socket {i}"))
        sock.is_on = True
        sock.turn_on = AsyncMock(return_value=Success(True))
        sock.turn_off = AsyncMock(return_value=Success(True))
        sock.device_id = f"123{i}"
        sock.parent_device_id = "123"
        sock.nickname = f"Nickname{i}"
        sockets.append(sock)

    device.sockets = sockets

    return device

def _mock_base_device(device: MagicMock) -> MagicMock:
    device.host = "1.2.3.4"
    device.nickname = "Nickname"
    device.device_id = "123"
    device.turn_on = AsyncMock(return_value=Success(True))
    device.turn_off = AsyncMock(return_value=Success(True))
    device.is_on = True
    device.model = "T100"
    device.firmware_version = "1.0.0"
    device.device_info.hardware_version = "1.0.0"
    device.mac = "1A-22-33-B4-C5-66"
    device.update = AsyncMock(return_value=None)
    device.registry = MockComponentsRegistry()
    device.add_component = MagicMock(side_effect=device.registry.add_component)
    device.get_component = MagicMock(side_effect=device.registry.get_component)
    device.has_component = MagicMock(side_effect=device.registry.has_component)
    return _mock_overheat(device)

def _mock_hub_child_device(device: MagicMock) -> MagicMock:
    device = _mock_base_device(device)
    device.parent_device_id = "parent_123"
    return device

class MockComponentsRegistry:

    def __init__(self):
        self._cs =[]

    def add_component(self, c: MagicMock):
        self._cs.append(c)

    def has_component(self, x) -> bool:
        for c in self._cs:
            if x == c.__class__:
                return True
        return False

    def get_component(self, x) -> MagicMock | None:
        for c in self._cs:
            if x == c.__class__:
                return c
        return None
