"""Test tapo switch."""
from unittest.mock import MagicMock

import pytest
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.light import ATTR_COLOR_MODE
from homeassistant.components.light import ATTR_COLOR_TEMP
from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
from homeassistant.components.light import ATTR_EFFECT
from homeassistant.components.light import ATTR_EFFECT_LIST
from homeassistant.components.light import ATTR_HS_COLOR
from homeassistant.components.light import ATTR_MAX_COLOR_TEMP_KELVIN
from homeassistant.components.light import ATTR_MAX_MIREDS
from homeassistant.components.light import ATTR_MIN_COLOR_TEMP_KELVIN
from homeassistant.components.light import ATTR_MIN_MIREDS
from homeassistant.components.light import ATTR_SUPPORTED_COLOR_MODES
from homeassistant.components.light import ColorMode
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.light import SERVICE_TURN_OFF
from homeassistant.components.light import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from plugp100.api.light_effect_preset import LightEffectPreset

from .conftest import extract_entity_id
from .conftest import mock_bulb
from .conftest import mock_led_strip
from .conftest import setup_platform


@pytest.mark.parametrize("tapo_device", [mock_bulb(), mock_led_strip()])
async def test_light_color_state(hass: HomeAssistant, tapo_device: MagicMock):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    state_entity = hass.states.get(entity_id)
    assert state_entity.state == "on"
    assert state_entity.attributes[ATTR_SUPPORTED_COLOR_MODES] == [
        ColorMode.BRIGHTNESS,
        ColorMode.COLOR_TEMP,
        ColorMode.HS,
        ColorMode.ONOFF,
    ]
    assert state_entity.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP
    assert state_entity.attributes[ATTR_BRIGHTNESS] == 255  # means 100 on tapo
    assert state_entity.attributes[ATTR_COLOR_TEMP] == 154  # is merids, means 6493K
    assert state_entity.attributes[ATTR_COLOR_TEMP_KELVIN] == 6493
    assert state_entity.attributes[ATTR_MAX_MIREDS] == 400
    assert state_entity.attributes[ATTR_MIN_MIREDS] == 153
    assert state_entity.attributes[ATTR_MAX_COLOR_TEMP_KELVIN] == 6500
    assert state_entity.attributes[ATTR_MIN_COLOR_TEMP_KELVIN] == 2500
    assert state_entity.attributes[ATTR_HS_COLOR] == (48.348, 2.014)


@pytest.mark.parametrize("tapo_device", [mock_bulb(), mock_led_strip()])
async def test_light_color_service_call(hass: HomeAssistant, tapo_device: MagicMock):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    assert hass.states.get(entity_id) is not None
    await hass.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    tapo_device.off.assert_called_once()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 100},
        blocking=True,
    )
    tapo_device.on.assert_called_once()
    tapo_device.set_brightness.assert_called_with(39)
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_COLOR_TEMP: 300},
        blocking=True,
    )
    tapo_device.set_color_temperature.assert_called_with(3333)
    tapo_device.set_hue_saturation.assert_not_called()
    tapo_device.set_color_temperature.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_HS_COLOR: (50, 10)},
        blocking=True,
    )
    tapo_device.set_hue_saturation.assert_called_with(50, 10)
    tapo_device.set_color_temperature.assert_not_called()


@pytest.mark.parametrize("tapo_device", [mock_led_strip()])
async def test_light_color_effects(hass: HomeAssistant, tapo_device: MagicMock):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    state_entity = hass.states.get(entity_id)
    assert state_entity.attributes[ATTR_EFFECT_LIST] == [
        effect.name.lower() for effect in LightEffectPreset
    ]
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: LightEffectPreset.Aurora.name},
        blocking=True,
    )
    tapo_device.set_light_effect.assert_called_with(
        LightEffectPreset.Aurora.to_effect()
    )
    tapo_device.set_light_effect_brightness.assert_not_called()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_BRIGHTNESS: 100,
            ATTR_EFFECT: LightEffectPreset.Aurora.name,
        },
        blocking=True,
    )
    tapo_device.set_light_effect_brightness.assert_called_with(
        LightEffectPreset.Aurora.to_effect(), 39
    )
    tapo_device.set_brightness.assert_not_called()


@pytest.mark.parametrize("tapo_device", [mock_bulb(), mock_led_strip()])
async def test_light_turn_on_with_attributes(
    hass: HomeAssistant, tapo_device: MagicMock
):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    hass.states.get(entity_id)
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 30, ATTR_HS_COLOR: (30, 10)},
        blocking=True,
    )
    assert tapo_device.on.called
    tapo_device.set_hue_saturation.assert_called_with(30, 10)
    tapo_device.set_brightness.assert_called_with(12)


@pytest.mark.parametrize("tapo_device", [mock_led_strip()])
async def test_light_turn_on_with_effect(hass: HomeAssistant, tapo_device: MagicMock):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_EFFECT: LightEffectPreset.Christmas.name,
            ATTR_BRIGHTNESS: 100,
        },
        blocking=True,
    )
    assert tapo_device.on.called
    tapo_device.set_light_effect.assert_called_with(
        LightEffectPreset.Christmas.to_effect()
    )
    tapo_device.set_light_effect_brightness.assert_called_with(
        LightEffectPreset.Christmas.to_effect(), 39
    )


@pytest.mark.parametrize("tapo_device", [mock_bulb(components_to_exclude=["color"])])
async def test_color_temp_only_light(hass: HomeAssistant, tapo_device: MagicMock):
    await setup_platform(hass, tapo_device, [LIGHT_DOMAIN])
    entity_id = await extract_entity_id(tapo_device, LIGHT_DOMAIN)
    state_entity = hass.states.get(entity_id)
    assert state_entity.attributes[ATTR_SUPPORTED_COLOR_MODES] == [
        ColorMode.BRIGHTNESS,
        ColorMode.COLOR_TEMP,
        ColorMode.ONOFF,
    ]
    assert state_entity.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 30, ATTR_COLOR_TEMP: 300},
        blocking=True,
    )
    tapo_device.set_color_temperature.assert_called_with(3333)
    tapo_device.set_hue_saturation.assert_not_called()
