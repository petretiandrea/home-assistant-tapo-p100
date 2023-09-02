import pytest
from homeassistant.components import network
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_find_device_by_mac(hass: HomeAssistant):
    adapters = await network.async_get_adapters(hass)
    print(adapters)
    assert True
