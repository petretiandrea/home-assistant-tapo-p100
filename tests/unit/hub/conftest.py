import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant) -> bool:
    return False