"""Global fixtures for tapo integration."""
import json
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiohttp import ClientSession
from plugp100.api.tapo_client import AuthCredential
from plugp100.api.tapo_client import PassthroughProtocol
from plugp100.api.tapo_client import TapoClient
from plugp100.api.tapo_client import TapoProtocol
from plugp100.common.functional.tri import Try
from plugp100.responses.tapo_response import TapoResponse
from pytest_homeassistant_custom_component.common import load_fixture

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture(scope="session")
def mock_protocol() -> TapoProtocol:
    return Mock(PassthroughProtocol)


@pytest.fixture(scope="session")
def tapo_client(mock_protocol: TapoProtocol):
    """Mock the Hue V1 api."""
    return create_mock_tapo_client(mock_protocol)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(scope="session")
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
