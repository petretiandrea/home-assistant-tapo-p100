from custom_components.tapo.const import HUB_PLATFORMS
from homeassistant.components.siren import DOMAIN as SIREN_DOMAIN
from homeassistant.components.siren import SERVICE_TURN_OFF
from homeassistant.components.siren import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from tests.conftest import mock_hub
from tests.conftest import setup_platform


# TODO: test volume
async def test_hub_siren_on(hass: HomeAssistant):
    device = mock_hub()
    await setup_platform(hass, device, HUB_PLATFORMS)
    entity_id = "siren.smart_hub_siren"
    state = hass.states.get(entity_id)
    assert state.state == "off"
    await hass.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert device.turn_alarm_on.called


async def test_hub_siren_off(hass: HomeAssistant):
    device = mock_hub()
    await setup_platform(hass, device, HUB_PLATFORMS)
    entity_id = "siren.smart_hub_siren"
    state = hass.states.get(entity_id)
    assert state.state == "off"
    await hass.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert device.turn_alarm_off.called
