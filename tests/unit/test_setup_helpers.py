"""Tests for setup_helpers."""
from unittest.mock import AsyncMock, patch

from plugp100.common.credentials import AuthCredential

from custom_components.tapo.setup_helpers import connect_with_discovery_fallback
from tests.conftest import mock_discovered_device


async def test_connect_with_discovery_fallback_uses_discovered_protocol():
    discovered_device = mock_discovered_device()
    credentials = AuthCredential("user", "pass")
    expected_device = object()

    with patch(
        "custom_components.tapo.setup_helpers.connect_discovered_device",
        AsyncMock(return_value=expected_device),
    ) as mock_connect_discovered:
        device = await connect_with_discovery_fallback(discovered_device, credentials)

    mock_connect_discovered.assert_called_once_with(
        discovered_device=discovered_device, credentials=credentials, session=None
    )
    assert device is expected_device


async def test_connect_with_discovery_fallback_falls_back_to_guessing():
    discovered_device = mock_discovered_device()
    credentials = AuthCredential("user", "pass")
    expected_device = object()

    with patch(
        "custom_components.tapo.setup_helpers.connect_discovered_device",
        AsyncMock(side_effect=Exception("Failed to determine the right tapo protocol")),
    ):
        with patch(
            "custom_components.tapo.setup_helpers.connect",
            AsyncMock(return_value=expected_device),
        ) as mock_connect:
            device = await connect_with_discovery_fallback(
                discovered_device, credentials
            )

    mock_connect.assert_called_once()
    called_config = mock_connect.call_args.kwargs["config"]
    assert called_config.host == discovered_device.ip
    assert called_config.port == discovered_device.mgt_encrypt_schm.http_port
    assert called_config.credentials == credentials
    assert called_config.device_type == discovered_device.device_type
    assert called_config.encryption_type is None
    assert device is expected_device


async def test_connect_with_discovery_fallback_uses_discovered_https_port():
    discovered_device = mock_discovered_device()
    discovered_device.mgt_encrypt_schm.is_support_https = True
    discovered_device.mgt_encrypt_schm.http_port = 4433
    credentials = AuthCredential("user", "pass")
    expected_device = object()

    with patch(
        "custom_components.tapo.setup_helpers.connect_discovered_device",
        AsyncMock(side_effect=Exception("Failed to determine the right tapo protocol")),
    ):
        with patch(
            "custom_components.tapo.setup_helpers.connect",
            AsyncMock(return_value=expected_device),
        ) as mock_connect:
            device = await connect_with_discovery_fallback(
                discovered_device, credentials
            )

    called_config = mock_connect.call_args.kwargs["config"]
    assert called_config.port == 4433
    assert device is expected_device
