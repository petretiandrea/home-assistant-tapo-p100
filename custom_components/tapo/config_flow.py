"""Config flow for tapo integration."""
import dataclasses
import logging
from typing import Any, Optional
import aiohttp

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant import data_entry_flow
from homeassistant.const import CONF_SCAN_INTERVAL
from plugp100.responses.device_state import DeviceInfo
from plugp100.api.tapo_client import TapoClient
from plugp100.responses.tapo_exception import TapoException, TapoError
from custom_components.tapo.utils import value_or_raise
from custom_components.tapo.const import (
    CONF_DEVICE_TYPE,
    DEFAULT_POLLING_RATE_S,
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ADVANCED_SETTINGS,
    STEP_INIT,
    STEP_ADVANCED_SETTINGS,
)  # pylint:disable=unused-import


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
        vol.Optional(CONF_ADVANCED_SETTINGS, description="Advanced settings"): bool,
    }
)

STEP_ADVANCED_CONFIGURATION = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL,
            description="Polling rate in seconds (e.g. 0.5 seconds means 500ms)",
            default=DEFAULT_POLLING_RATE_S,
        ): vol.All(vol.Coerce(float), vol.Clamp(min=0)),
    }
)


@dataclasses.dataclass(frozen=False)
class FirstStepData:
    state: Optional[DeviceInfo]
    user_input: Optional[dict[str, Any]]


@config_entries.HANDLERS.register(DOMAIN)
class TapoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for tapo."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        super().__init__()
        self.first_step_data: Optional[FirstStepData] = None

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""

        errors = {}

        if user_input is not None:
            try:
                if not user_input[CONF_HOST]:
                    raise InvalidHost
                api = await self._try_setup_api(user_input)
                unique_data = await self._get_first_data_from_api(api)
                unique_id = unique_data.device_id
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                self.hass.data.setdefault(DOMAIN, {})
                self.hass.data[DOMAIN][f"{unique_id}_api"] = api

                if user_input.get(CONF_ADVANCED_SETTINGS, False):
                    self.first_step_data = FirstStepData(unique_data, user_input)
                    return await self.async_step_advanced_config()
                else:
                    return self.async_create_entry(
                        title=unique_data.nickname,
                        data=user_input,
                    )
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

        return self.async_show_form(
            step_id=STEP_INIT, data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_advanced_config(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            polling_rate = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
            return self.async_create_entry(
                title=self.first_step_data.state.nickname,
                data={
                    CONF_SCAN_INTERVAL: polling_rate,
                    **self.first_step_data.user_input,
                },
            )
        else:
            return self.async_show_form(
                step_id=STEP_ADVANCED_SETTINGS,
                data_schema=STEP_ADVANCED_CONFIGURATION,
                errors=errors,
            )

    async def _get_first_data_from_api(self, api: TapoClient) -> DeviceInfo:
        try:
            return value_or_raise(
                (await api.get_device_info()).map(lambda x: DeviceInfo(**x))
            )
        except TapoException as error:
            self._raise_from_tapo_exception(error)
        except (aiohttp.ClientError, Exception) as error:
            raise CannotConnect from error

    async def _try_setup_api(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> TapoClient:
        try:
            session = async_create_clientsession(self.hass)
            client = TapoClient(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD], session
            )
            return value_or_raise(
                (await client.login(user_input[CONF_HOST])).map(lambda _: client)
            )
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
