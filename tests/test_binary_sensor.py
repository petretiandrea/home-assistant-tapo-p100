"""Test tapo switch."""
import pytest
from custom_components.tapo.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from plugp100.api.tapo_client import TapoProtocol

from .conftest import fixture_tapo_map
from .conftest import setup_platform


@pytest.mark.parametrize(
    "device_state_fixture, device_id",
    [("plug_p105.json", "80225A84E5F52C914E409EF8CCE7D68D20FAA0B9")],
)
async def test_switch_setup(
    hass: HomeAssistant,
    mock_protocol: TapoProtocol,
    device_state_fixture: str,
    device_id: str,
):
    device_registry = dr.async_get(hass)
    await mock_protocol.load_test_data(fixture_tapo_map(device_state_fixture))

    await setup_platform(hass, ["binary_sensor"])
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get("binary_sensor.albero_natale_overheat")
    device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
    assert state_entity is not None
    assert state_entity.state == "off"
    assert state_entity.attributes["device_class"] == "heat"
    assert "overheat" in state_entity.attributes["friendly_name"].lower()
    assert device is not None
