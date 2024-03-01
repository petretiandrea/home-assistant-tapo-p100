from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import HUB_PLATFORMS
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.siren import DOMAIN as SIREN_DOMAIN
from homeassistant.components.siren import SERVICE_TURN_OFF
from homeassistant.components.siren import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import mock_hub
from .conftest import setup_platform


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


async def test_hub_overheat_sensor(
    hass: HomeAssistant,
):
    device_registry = dr.async_get(hass)
    device = mock_hub()
    entry = await setup_platform(hass, device, [BINARY_SENSOR_DOMAIN])
    entity_id = "binary_sensor.smart_hub_overheat"
    assert len(hass.states.async_all()) == 1

    state_entity = hass.states.get(entity_id)
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert state_entity is not None
    assert state_entity.state == "off"
    assert state_entity.attributes["device_class"] == "heat"
    assert "overheat" in state_entity.attributes["friendly_name"].lower()
    assert device is not None
