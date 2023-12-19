"""Test tapo switch."""
import pytest
from custom_components.tapo.const import DOMAIN
from homeassistant.components.switch import SERVICE_TURN_OFF
from homeassistant.components.switch import SERVICE_TURN_ON
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

    await setup_platform(hass, ["switch"])
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get("switch.albero_natale")
    device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
    assert state_entity is not None
    assert state_entity.state == "on"
    assert state_entity.attributes["device_class"] == "outlet"
    assert device is not None


@pytest.mark.parametrize("device_state_fixture", ["plug_p105.json"])
async def test_switch_turn_on_service(
    hass: HomeAssistant, mock_protocol: TapoProtocol, device_state_fixture: str
):
    await mock_protocol.load_test_data(fixture_tapo_map(device_state_fixture))
    await setup_platform(hass, ["switch"])
    await hass.services.async_call(
        "switch", SERVICE_TURN_ON, {"entity_id": "switch.albero_natale"}, blocking=True
    )
    assert mock_protocol.send_request.called
    assert mock_protocol.send_request.call_args.args[0].params == {"device_on": True}
    assert mock_protocol.send_request.call_args.args[0].method == "set_device_info"


@pytest.mark.parametrize("device_state_fixture", ["plug_p105.json"])
async def test_switch_turn_off_service(
    hass: HomeAssistant, mock_protocol: TapoProtocol, device_state_fixture: str
):
    await mock_protocol.load_test_data(fixture_tapo_map(device_state_fixture))
    await setup_platform(hass, ["switch"])
    await hass.services.async_call(
        "switch", SERVICE_TURN_OFF, {"entity_id": "switch.albero_natale"}, blocking=True
    )
    assert mock_protocol.send_request.called
    assert mock_protocol.send_request.call_args.args[0].params == {"device_on": False}
    assert mock_protocol.send_request.call_args.args[0].method == "set_device_info"
