from custom_components.tapo import CONF_DISCOVERED_DEVICE_INFO
from custom_components.tapo import CONF_HOST
from custom_components.tapo import CONF_MAC
from custom_components.tapo import CONF_TRACK_DEVICE
from custom_components.tapo import DEFAULT_POLLING_RATE_S
from custom_components.tapo import DOMAIN
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from plugp100.discovery.discovered_device import DiscoveredDevice

from .conftest import IP_ADDRESS
from .conftest import MAC_ADDRESS


async def test_discovery_auth(
    hass: HomeAssistant, mock_discovery: DiscoveredDevice
) -> None:
    """Test authenticated discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_INTEGRATION_DISCOVERY,
            CONF_DISCOVERED_DEVICE_INFO: mock_discovery,
        },
        data={
            CONF_HOST: IP_ADDRESS,
            CONF_MAC: MAC_ADDRESS,
            CONF_SCAN_INTERVAL: DEFAULT_POLLING_RATE_S,
            CONF_TRACK_DEVICE: False,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] == "form"
    assert result["step_id"] == "discovery_auth_confirm"

    auth_result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )

    assert auth_result["type"] is FlowResultType.CREATE_ENTRY
    assert auth_result["context"]["unique_id"] == MAC_ADDRESS
    assert auth_result["data"][CONF_USERNAME] == "fake_username"
    assert auth_result["data"][CONF_PASSWORD] == "fake_password"
    assert auth_result["data"][CONF_HOST] == mock_discovery.ip
    assert auth_result["data"][CONF_TRACK_DEVICE] is False
    assert auth_result["data"][CONF_SCAN_INTERVAL] == 30
    assert auth_result["context"][CONF_DISCOVERED_DEVICE_INFO] == mock_discovery
