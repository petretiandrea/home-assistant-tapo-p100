"""Test tapo switch."""
from unittest.mock import MagicMock

import pytest
from custom_components.tapo.const import DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
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
async def test_switch_overheat(hass: HomeAssistant, device: MagicMock):
    device_registry = dr.async_get(hass)
    await setup_platform(hass, device, [BINARY_SENSOR_DOMAIN])
    entity_id = await extract_entity_id(device, BINARY_SENSOR_DOMAIN, "overheat")
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get(entity_id)
    device = device_registry.async_get_device(identifiers={(DOMAIN, device.device_id)})
    assert state_entity is not None
    assert state_entity.state == "off"
    assert state_entity.attributes["device_class"] == "heat"
    assert "overheat" in state_entity.attributes["friendly_name"].lower()
    assert device is not None
