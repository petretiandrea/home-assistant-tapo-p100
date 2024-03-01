"""Test tapo switch."""
from unittest.mock import MagicMock

import pytest
from custom_components.tapo.const import DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import extract_entity_id
from .conftest import mock_hub
from .conftest import mock_switch
from .conftest import setup_platform


@pytest.mark.parametrize("device", [mock_switch(), mock_hub()])
async def test_signal_sensor(hass: HomeAssistant, device: MagicMock):
    device_registry = dr.async_get(hass)
    entry = await setup_platform(hass, device, [SENSOR_DOMAIN])
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get(
        await extract_entity_id(device, "sensor", "signal_level")
    )
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert state_entity is not None
    assert state_entity.state is not None
    assert state_entity.attributes["device_class"] == "signal_strength"
    assert "signal level" in state_entity.attributes["friendly_name"].lower()
    assert device is not None
