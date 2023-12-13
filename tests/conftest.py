"""Global fixtures for tapo integration."""
import json
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiohttp import ClientSession
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_TRACK_DEVICE
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DOMAIN
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from plugp100.api.tapo_client import AuthCredential
from plugp100.api.tapo_client import PassthroughProtocol
from plugp100.api.tapo_client import TapoClient
from plugp100.api.tapo_client import TapoProtocol
from plugp100.common.functional.tri import Try
from plugp100.responses.tapo_response import TapoResponse
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture(scope="session")
def mock_protocol() -> TapoProtocol:
    mock = Mock(PassthroughProtocol)

    async def load_test_data(response: Try[TapoResponse]):
        mock.send_request = AsyncMock(return_value=response)

    async def load_test_data2(data: list[Try[TapoResponse]]):
        mock.send_request = AsyncMock(side_effect=data)

    mock.load_test_data = load_test_data
    mock.load_test_data2 = load_test_data2
    return mock


@pytest.fixture(scope="session")
def tapo_client(mock_protocol: TapoProtocol):
    """Mock the Hue V1 api."""
    return create_mock_tapo_client(mock_protocol)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(scope="session", autouse=True)
def patch_setup_api(tapo_client: TapoClient):
    with patch(
        target="custom_components.tapo.setup_helpers.connect_tapo_client",
        return_value=tapo_client,
    ):
        yield


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    return True


def create_mock_tapo_client(protocol: TapoProtocol) -> TapoClient:
    return TapoClient(
        auth_credential=AuthCredential("mock", "mock"),
        url="http://localhost:mock",
        protocol=protocol,
        http_session=Mock(ClientSession),
    )


def fixture_tapo_responses(resource: str) -> list[Try[TapoResponse]]:
    elems = json.loads(load_fixture(resource))
    return [tapo_response_of(e) for e in elems]


def fixture_tapo_response(resource: str) -> Try[TapoResponse]:
    return tapo_response_of(json.loads(load_fixture(resource)))


def fixture_tapo_response_child(resource: str) -> Try[TapoResponse]:
    return tapo_response_of(
        {
            "responseData": {
                "result": {
                    "responses": [{"result": json.loads(load_fixture(resource))}]
                }
            }
        }
    )


def tapo_response_of(payload: dict[str, any]) -> Try[TapoResponse]:
    return Try.of(TapoResponse(error_code=0, result=payload, msg=""))


async def setup_platform(hass: HomeAssistant, platforms: list[str]):
    hass.config.components.add(DOMAIN)
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.2.3.4",
            CONF_USERNAME: "mock",
            CONF_PASSWORD: "mock",
            CONF_SCAN_INTERVAL: 5000,
            CONF_TRACK_DEVICE: False,
        },
        version=6,
        entry_id="test",
        unique_id="test",
    )

    config_entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_forward_entry_setup"):
        await hass.config_entries.async_setup(config_entry.entry_id)
        assert await async_setup_component(hass, DOMAIN, {}) is True
        await hass.async_block_till_done()

    for platform in platforms:
        await hass.config_entries.async_forward_entry_setup(config_entry, platform)
    await hass.async_block_till_done()

    return config_entry
