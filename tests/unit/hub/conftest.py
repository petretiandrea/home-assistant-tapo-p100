from homeassistant.core import HomeAssistant
import pytest


@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant) -> bool:
    return False
