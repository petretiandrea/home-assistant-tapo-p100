from unittest.mock import AsyncMock
from unittest.mock import patch

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import HUB_PLATFORMS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from plugp100.api.tapo_client import TapoProtocol
from plugp100.common.functional.tri import Failure
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import fixture_tapo_map

MOCK_CONFIG_ENTRY_DATA = {
    CONF_HOST: "1.2.3.4",
    CONF_USERNAME: "mock",
    CONF_PASSWORD: "mock",
    CONF_SCAN_INTERVAL: 5000,
    CONF_TRACK_DEVICE: False,
    "is_hub": True,
}


async def test_hub_setup(hass: HomeAssistant, mock_protocol: TapoProtocol):
    config_entry = MockConfigEntry(
        domain="tapo",
        data=MOCK_CONFIG_ENTRY_DATA,
        version=6,
        entry_id="test",
        unique_id="test",
    )

    await mock_protocol.load_test_data(fixture_tapo_map("hub.json"))
    config_entry.add_to_hass(hass)
    device_registry: dr.DeviceRegistry = dr.async_get(hass)

    with patch.object(hass.config_entries, "async_forward_entry_setup") as mock_forward:
        assert await hass.config_entries.async_setup(config_entry.entry_id) is True
        await hass.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED
        assert {c[1][1] for c in mock_forward.mock_calls} == set(HUB_PLATFORMS)
        assert len(device_registry.devices) == 2


async def test_hub_setup_retry_when_error(
    hass: HomeAssistant, mock_protocol: TapoProtocol
):
    config_entry = MockConfigEntry(
        domain="tapo", data=MOCK_CONFIG_ENTRY_DATA, version=6, entry_id="test"
    )
    config_entry.add_to_hass(hass)

    mock_protocol.send_request = AsyncMock(
        return_value=Failure(Exception("generic error"))
    )

    with patch.object(
        mock_protocol, "send_request", side_effect=[Failure(Exception("generic error"))]
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id) is False
        await hass.async_block_till_done()
        assert config_entry.state is ConfigEntryState.SETUP_RETRY
