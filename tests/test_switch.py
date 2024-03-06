"""Test tapo switch."""
from custom_components.tapo.const import DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import SERVICE_TURN_OFF
from homeassistant.components.switch import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import extract_entity_id
from .conftest import mock_plug
from .conftest import mock_plug_strip
from .conftest import setup_platform


async def test_switch_setup(hass: HomeAssistant):
    device_registry = dr.async_get(hass)
    device = mock_plug()
    await setup_platform(hass, device, [SWITCH_DOMAIN])
    entity_id = await extract_entity_id(device, SWITCH_DOMAIN)
    state_entity = hass.states.get(entity_id)
    device = device_registry.async_get_device(identifiers={(DOMAIN, device.device_id)})
    assert state_entity is not None
    assert state_entity.state == "on"
    assert state_entity.attributes["device_class"] == "outlet"
    assert device is not None


async def test_switch_turn_on_service(hass: HomeAssistant):
    device = mock_plug()
    entity_id = await extract_entity_id(device, SWITCH_DOMAIN)
    assert await setup_platform(hass, device, [SWITCH_DOMAIN]) is not None
    state = hass.states.get(entity_id)
    assert state.state == "on"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.on.assert_called_once()


async def test_switch_turn_off_service(hass: HomeAssistant):
    device = mock_plug()
    entity_id = await extract_entity_id(device, SWITCH_DOMAIN)
    assert await setup_platform(hass, device, [SWITCH_DOMAIN]) is not None
    state = hass.states.get(entity_id)
    assert state.state == "on"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.off.assert_called_once()


async def test_plug_strip_child_onoff(hass: HomeAssistant):
    device = mock_plug_strip()
    await extract_entity_id(device, SWITCH_DOMAIN)
    assert await setup_platform(hass, device, [SWITCH_DOMAIN]) is not None
    expected_children_state = {
        "switch.p300_plug1": {"value": "on"},
        "switch.p300_plug2": {"value": "on"},
        "switch.p300_plug3": {"value": "on"},
    }
    for children_id, state in expected_children_state.items():
        assert hass.states.get(children_id).state == state["value"]
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: children_id},
            blocking=True,
        )
        device.on.assert_called_once()
        device.on.reset_mock()
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: children_id},
            blocking=True,
        )
        device.off.assert_called_once()
        device.off.reset_mock()
