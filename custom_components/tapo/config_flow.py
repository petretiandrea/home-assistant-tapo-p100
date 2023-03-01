"""Config flow for tapo integration."""
import logging
from typing import Any, Optional
import aiohttp

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant import data_entry_flow
from plugp100 import TapoApiClient, TapoApiClientConfig, TapoException, TapoError

from custom_components.tapo.const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
)


_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_HOST,
            description="The IP address of your tapo device (must be static)",
        ): str,
        vol.Required(
            CONF_USERNAME, description="The username used with Tapo App, so your email"
        ): str,
        vol.Required(CONF_PASSWORD, description="The password used with Tapo App"): str,
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class TapoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for tapo."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        errors = {}

        try:
            if not user_input[CONF_HOST]:
                raise InvalidHost
            api = await self._try_setup_api(user_input)
            unique_data = await self._get_unique_data_from_api(api)
            unique_id = unique_data["unique_id"]
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            self.hass.data.setdefault(DOMAIN, {})
            self.hass.data[DOMAIN][f"{unique_id}_api"] = api
        except InvalidAuth as error:
            errors["base"] = "invalid_auth"
            _LOGGER.exception("Failed to setup, invalid auth %s", str(error))
        except CannotConnect as error:
            errors["base"] = "cannot_connect"
            _LOGGER.exception("Failed to setup cannot connect %s", str(error))
        except InvalidHost as error:
            errors["base"] = "invalid_hostname"
            _LOGGER.exception("Failed to setup invalid host %s", str(error))
        except data_entry_flow.AbortFlow:
            return self.async_abort(reason="already_configured")
        except Exception as error:  # pylint: disable=broad-except
            errors["base"] = "unknown"
            _LOGGER.exception("Failed to setup %s", str(error), exc_info=True)
        else:
            return self.async_create_entry(title=unique_data["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _get_unique_data_from_api(self, api: TapoApiClient) -> dict[str, Any]:
        try:
            state = await api.get_state()
            return {"title": state.nickname, "unique_id": state.device_id}
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except (aiohttp.ClientError, Exception) as error:
            raise CannotConnect from error

    async def _try_setup_api(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> TapoApiClient:
        try:
            session = async_create_clientsession(self.hass)
            config = TapoApiClientConfig(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                session,
            )
            client = TapoApiClient.from_config(config)
            await client.login()
            return client
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except (aiohttp.ClientError, Exception) as error:
            raise CannotConnect from error

    def _raise_from_tapo_exception(self, exception: TapoException):
        _LOGGER.error("Tapo exception %s", str(exception.error_code))
        if exception.error_code == TapoError.INVALID_CREDENTIAL.value:
            raise InvalidAuth from exception
        else:
            raise CannotConnect from exception


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
