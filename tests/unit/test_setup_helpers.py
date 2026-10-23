from unittest.mock import AsyncMock, MagicMock, patch

from plugp100.common.credentials import AuthCredential
from plugp100.common.functional.tri import Failure, Success
import pytest

from custom_components.tapo.setup_helpers import connect_with_discovery_fallback
from tests.conftest import mock_discovered_device

CREDENTIALS = AuthCredential("user", "password")


def _device(device_info=Success({"model": "P115"})) -> MagicMock:
    device = MagicMock()
    device.client.get_device_info = AsyncMock(return_value=device_info)
    return device


class TestConnectWithDiscoveryFallback:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.discovered_device = mock_discovered_device()

    async def test_uses_discovered_protocol_when_it_works(self):
        device = _device()
        with (
            patch(
                "custom_components.tapo.setup_helpers.connect_discovered_device",
                AsyncMock(return_value=device),
            ) as discovered_connect,
            patch(
                "custom_components.tapo.setup_helpers.connect",
                AsyncMock(),
            ) as guessing_connect,
        ):
            result = await connect_with_discovery_fallback(
                self.discovered_device, CREDENTIALS
            )

        assert result is device
        discovered_connect.assert_awaited_once()
        guessing_connect.assert_not_awaited()

    async def test_guesses_when_connect_raises(self):
        guessed = _device()
        with (
            patch(
                "custom_components.tapo.setup_helpers.connect_discovered_device",
                AsyncMock(side_effect=Exception("unsupported encryption scheme")),
            ),
            patch(
                "custom_components.tapo.setup_helpers.connect",
                AsyncMock(return_value=guessed),
            ) as guessing_connect,
        ):
            result = await connect_with_discovery_fallback(
                self.discovered_device, CREDENTIALS
            )

        assert result is guessed
        guessing_connect.assert_awaited_once()

    async def test_guesses_when_the_first_exchange_fails(self):
        """A protocol the device no longer answers only fails on first use.

        `connect_discovered_device` builds the protocol from the advertised
        encryption scheme without talking to the device, so a device that has
        stopped offering that protocol -- after a firmware update, say -- is
        only discovered when a request is made.
        """
        unreachable = _device(Failure(Exception("discover response missing protocol")))
        guessed = _device()
        with (
            patch(
                "custom_components.tapo.setup_helpers.connect_discovered_device",
                AsyncMock(return_value=unreachable),
            ),
            patch(
                "custom_components.tapo.setup_helpers.connect",
                AsyncMock(return_value=guessed),
            ) as guessing_connect,
        ):
            result = await connect_with_discovery_fallback(
                self.discovered_device, CREDENTIALS
            )

        assert result is guessed
        guessing_connect.assert_awaited_once()

    async def test_guessing_keeps_host_and_port_of_the_discovered_device(self):
        guessed = _device()
        with (
            patch(
                "custom_components.tapo.setup_helpers.connect_discovered_device",
                AsyncMock(side_effect=Exception("nope")),
            ),
            patch(
                "custom_components.tapo.setup_helpers.connect",
                AsyncMock(return_value=guessed),
            ) as guessing_connect,
        ):
            await connect_with_discovery_fallback(self.discovered_device, CREDENTIALS)

        config = guessing_connect.await_args.kwargs["config"]
        assert config.host == self.discovered_device.ip
        assert config.port == self.discovered_device.mgt_encrypt_schm.http_port
        assert config.device_type == self.discovered_device.device_type
        assert config.encryption_type is None
