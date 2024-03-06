import logging

from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential

_LOGGGER = logging.getLogger(__name__)


async def create_api_from_config(
    hass: HomeAssistant, config: ConfigEntry
) -> TapoClient:
    credential = AuthCredential(
        config.data.get(CONF_USERNAME), config.data.get(CONF_PASSWORD)
    )
    _LOGGGER.debug(
        "Creating new API to create a coordinator for %s to address %s",
        config.unique_id,
        config.data.get(CONF_HOST),
    )
    session = async_create_clientsession(hass)
    host, port = get_host_port(config.data.get(CONF_HOST))
    return TapoClient.create(credential, address=host, port=port, http_session=session)


def get_host_port(host_user_input: str) -> (str, int):
    if ":" in host_user_input:
        parts = host_user_input.split(":", 1)
        return parts[0], int(parts[1])
    return host_user_input, 80
