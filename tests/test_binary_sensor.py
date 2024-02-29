"""Test tapo switch."""
from custom_components.tapo.const import DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import mock_switch
from .conftest import setup_platform


async def test_switch_overheat(hass: HomeAssistant):
    device_registry = dr.async_get(hass)
    device = mock_switch()
    entry = await setup_platform(hass, device, [BINARY_SENSOR_DOMAIN])
    entity_id = "binary_sensor.albero_natale_overheat"
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get(entity_id)
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert state_entity is not None
    assert state_entity.state == "off"
    assert state_entity.attributes["device_class"] == "heat"
    assert "overheat" in state_entity.attributes["friendly_name"].lower()
    assert device is not None
