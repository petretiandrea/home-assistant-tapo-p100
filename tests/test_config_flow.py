from unittest.mock import AsyncMock
from unittest.mock import patch

from custom_components.tapo import CONF_DISCOVERED_DEVICE_INFO
from custom_components.tapo import CONF_HOST
from custom_components.tapo import CONF_MAC
from custom_components.tapo import DEFAULT_POLLING_RATE_S
from custom_components.tapo import DOMAIN
from custom_components.tapo.const import STEP_DISCOVERY_REQUIRE_AUTH
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from plugp100.discovery.discovered_device import DiscoveredDevice
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import IP_ADDRESS
from .conftest import MAC_ADDRESS


async def test_discovery_auth(
    hass: HomeAssistant, mock_discovery: DiscoveredDevice
) -> None:
    """Test step required authentication on discovery."""
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
        },
    )
    await hass.async_block_till_done()
    assert result["type"] == "form"
    assert result["step_id"] == STEP_DISCOVERY_REQUIRE_AUTH

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
    assert auth_result["data"][CONF_SCAN_INTERVAL] == 30
    assert auth_result["context"][CONF_DISCOVERED_DEVICE_INFO] == mock_discovery


async def test_discovery_ip_change_dhcp(
    hass: HomeAssistant, mock_discovery: DiscoveredDevice
) -> None:
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: mock_discovery.ip,
            CONF_USERNAME: "mock",
            CONF_PASSWORD: "mock",
            CONF_SCAN_INTERVAL: 5000,
        },
        version=8,
        unique_id=dr.format_mac(mock_discovery.mac),
    )
    with patch(
        "plugp100.api.tapo_client.TapoClient.get_device_info",
        AsyncMock(side_effect=Exception("Something wrong")),
    ):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == config_entries.ConfigEntryState.SETUP_RETRY

    with patch(
        "custom_components.tapo.config_flow.discover_tapo_device",
        AsyncMock(return_value=mock_discovery),
    ):
        discovery_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=dhcp.DhcpServiceInfo(
                ip="127.0.0.2", macaddress=MAC_ADDRESS, hostname="hostname"
            ),
        )
        assert discovery_result["type"] is FlowResultType.ABORT
        assert discovery_result["reason"] == "already_configured"
        assert mock_config_entry.data[CONF_HOST] == "127.0.0.2"
