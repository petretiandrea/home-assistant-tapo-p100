"""Test tapo switch."""
from custom_components.tapo.const import DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import SERVICE_TURN_OFF
from homeassistant.components.switch import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import mock_switch
from .conftest import setup_platform


async def test_switch_setup(hass: HomeAssistant):
    device_registry = dr.async_get(hass)
    device = mock_switch()
    entry = await setup_platform(hass, device, [SWITCH_DOMAIN])

    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get("switch.albero_natale")
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert state_entity is not None
    assert state_entity.state == "on"
    assert state_entity.attributes["device_class"] == "outlet"
    assert device is not None


async def test_switch_turn_on_service(hass: HomeAssistant):
    device = mock_switch()
    assert await setup_platform(hass, device, [SWITCH_DOMAIN]) is not None
    state = hass.states.get("switch.albero_natale")
    assert state.state == "on"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.albero_natale"},
        blocking=True,
    )
    device.on.assert_called_once()


async def test_switch_turn_off_service(hass: HomeAssistant):
    device = mock_switch()
    assert await setup_platform(hass, device, [SWITCH_DOMAIN]) is not None
    state = hass.states.get("switch.albero_natale")
    assert state.state == "on"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.albero_natale"},
        blocking=True,
    )
    device.off.assert_called_once()
