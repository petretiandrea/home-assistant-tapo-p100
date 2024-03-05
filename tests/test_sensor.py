"""Test tapo switch."""
from unittest.mock import MagicMock

import pytest
from custom_components.tapo.const import DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import extract_entity_id
from .conftest import mock_bulb
from .conftest import mock_hub
from .conftest import mock_led_strip
from .conftest import mock_plug
from .conftest import mock_plug_strip
from .conftest import setup_platform


@pytest.mark.parametrize(
    "device",
    [mock_plug(), mock_hub(), mock_plug_strip(), mock_bulb(), mock_led_strip()],
)
async def test_signal_sensor(hass: HomeAssistant, device: MagicMock):
    device_registry = dr.async_get(hass)
    await setup_platform(hass, device, [SENSOR_DOMAIN])
    state_entity = hass.states.get(
        await extract_entity_id(device, SENSOR_DOMAIN, "signal_level")
    )
    device = device_registry.async_get_device(identifiers={(DOMAIN, device.device_id)})
    assert state_entity is not None
    assert state_entity.state is not None
    assert state_entity.attributes["device_class"] == "signal_strength"
    assert "signal level" in state_entity.attributes["friendly_name"].lower()
    assert device is not None


# TODO: test unit of measure
@pytest.mark.parametrize("device", [mock_plug(with_emeter=True)])
async def test_switch_emeter(hass: HomeAssistant, device: MagicMock):
    entity_id = await extract_entity_id(device, SENSOR_DOMAIN)
    assert await setup_platform(hass, device, [SENSOR_DOMAIN]) is not None
    expected_emeter = {
        f"{entity_id}_current_power": {"value": 0.0012},
        f"{entity_id}_today_energy": {"value": 0.0},
        f"{entity_id}_month_energy": {"value": 1.421},
        f"{entity_id}_today_runtime": {"value": 3},
        f"{entity_id}_month_runtime": {"value": 19742},
    }
    for state_id, values in expected_emeter.items():
        assert hass.states.get(state_id).state == str(values["value"])
