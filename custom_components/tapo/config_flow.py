"""Config flow for tapo integration."""
import dataclasses
import logging
from typing import Any
from typing import Optional

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant import data_entry_flow
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import DiscoveryInfoType
from plugp100.common.credentials import AuthCredential
from plugp100.discovery.discovered_device import DiscoveredDevice
from plugp100.new.device_factory import DeviceConnectConfiguration, connect
from plugp100.new.tapodevice import TapoDevice
from plugp100.responses.tapo_exception import TapoError
from plugp100.responses.tapo_exception import TapoException

from custom_components.tapo.const import CONF_ADVANCED_SETTINGS
from custom_components.tapo.const import CONF_DISCOVERED_DEVICE_INFO
from custom_components.tapo.const import CONF_HOST
from custom_components.tapo.const import CONF_MAC
from custom_components.tapo.const import CONF_PASSWORD
from custom_components.tapo.const import CONF_USERNAME
from custom_components.tapo.const import DEFAULT_POLLING_RATE_S
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.const import STEP_ADVANCED_SETTINGS
from custom_components.tapo.const import STEP_DISCOVERY_REQUIRE_AUTH
from custom_components.tapo.const import STEP_INIT
from custom_components.tapo.discovery import discover_tapo_device
from custom_components.tapo.errors import CannotConnect
from custom_components.tapo.errors import InvalidAuth
from custom_components.tapo.errors import InvalidHost
from custom_components.tapo.setup_helpers import get_host_port, create_aiohttp_session

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

STEP_AUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_USERNAME, description="The username used with Tapo App, so your email"
        ): str,
        vol.Required(CONF_PASSWORD, description="The password used with Tapo App"): str,
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


def step_options(entry: config_entries.ConfigEntry) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                description="The IP address of your tapo device (must be static)",
                default=entry.data.get(CONF_HOST),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                description="Polling rate in seconds (e.g. 0.5 seconds means 500ms)",
                default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S),
            ): vol.All(vol.Coerce(float), vol.Clamp(min=1)),
        }
    )


@dataclasses.dataclass(frozen=False)
class FirstStepData:
    device: Optional[TapoDevice]
    user_input: Optional[dict[str, Any]]


@config_entries.HANDLERS.register(DOMAIN)
class TapoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for tapo."""

    VERSION = 5
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        super().__init__()
        self.first_step_data: Optional[FirstStepData] = None
        self._discovered_info: DiscoveredDevice | None = None

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> data_entry_flow.FlowResult:
        """Handle discovery via dhcp."""
        mac_address = dr.format_mac(discovery_info.macaddress)
        if discovered_device := await discover_tapo_device(discovery_info.ip):
            return await self._async_handle_discovery(
                discovery_info.ip, mac_address, discovered_device
            )

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> data_entry_flow.FlowResult:
        """Handle integration discovery."""
        discovered_device = DiscoveredDevice.from_dict(discovery_info[CONF_DISCOVERED_DEVICE_INFO])
        return await self._async_handle_discovery(
            discovery_info[CONF_HOST],
            discovery_info[CONF_MAC],
            discovered_device,
        )

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        self.hass.data.setdefault(DOMAIN, {})

        errors = {}

        if user_input is not None:
            try:
                device = await self._async_get_device(user_input)
                await self.async_set_unique_id(dr.format_mac(device.mac))
                self._abort_if_unique_id_configured()
                self._async_abort_entries_match({CONF_HOST: device.host})

                if user_input.get(CONF_ADVANCED_SETTINGS, False):
                    self.first_step_data = FirstStepData(device, user_input)
                    return await self.async_step_advanced_config()
                else:
                    return await self._async_create_config_entry_from_device_info(
                        device, user_input
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)

    async def async_step_advanced_config(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            polling_rate = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S)
            return self.async_create_entry(
                title=self.first_step_data.device.nickname,
                data=self.first_step_data.user_input
                | {CONF_SCAN_INTERVAL: polling_rate},
            )
        else:
            return self.async_show_form(
                step_id=STEP_ADVANCED_SETTINGS,
                data_schema=STEP_ADVANCED_CONFIGURATION,
                errors=errors,
            )

    async def _async_handle_discovery(
        self,
        host: str,
        mac_address: str,
        discovered_device: DiscoveredDevice,
    ) -> data_entry_flow.FlowResult:
        self._discovered_info = discovered_device
        existing_entry = await self.async_set_unique_id(
            mac_address, raise_on_progress=False
        )
        if existing_entry:
            if result := self._recover_config_on_entry_error(
                existing_entry, discovered_device.ip
            ):
                return result

        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._async_abort_entries_match({CONF_HOST: host})

        if is_supported_device(discovered_device):
            return await self.async_step_discovery_auth_confirm()
        else:
            return self.async_abort(reason="Device not supported")

    async def async_step_discovery_auth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        assert self._discovered_info is not None
        errors = {}

        if user_input:
            try:
                device = await self._async_get_device_from_discovered(
                    self._discovered_info, user_input
                )
                await self.async_set_unique_id(dr.format_mac(device.mac))
                self._abort_if_unique_id_configured()
            except InvalidAuth as error:
                errors["base"] = "invalid_auth"
                _LOGGER.exception("Failed to setup, invalid auth %s", str(error))
            except CannotConnect as error:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Failed to setup cannot connect %s", str(error))
            except InvalidHost as error:
                errors["base"] = "invalid_hostname"
                _LOGGER.exception("Failed to setup invalid host %s", str(error))
            else:
                return await self._async_create_config_entry_from_device_info(
                    device, user_input
                )

        discovery_data = {
            "name": self._discovered_info.device_model,
            "mac": self._discovered_info.mac.replace("-", "")[:5],
            "host": self._discovered_info.ip,
        }
        self.context.update({"title_placeholders": discovery_data})
        return self.async_show_form(
            step_id=STEP_DISCOVERY_REQUIRE_AUTH,
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders=discovery_data,
        )

    @callback
    def _recover_config_on_entry_error(
        self, entry: ConfigEntry, host: str
    ) -> data_entry_flow.FlowResult | None:
        if entry.state not in (
            ConfigEntryState.SETUP_ERROR,
            ConfigEntryState.SETUP_RETRY,
        ):
            return None
        if entry.data[CONF_HOST] != host:
            return self.async_update_reload_and_abort(
                entry, data={**entry.data, CONF_HOST: host}, reason="already_configured"
            )
        return None

    async def _async_create_config_entry_from_device_info(
        self, device: TapoDevice, options: dict[str, Any]
    ):
        return self.async_create_entry(
            title=device.nickname,
            data=options
            | {
                CONF_HOST: device.host,
                CONF_MAC: device.mac,
                CONF_SCAN_INTERVAL: DEFAULT_POLLING_RATE_S,
                CONF_DISCOVERED_DEVICE_INFO: self._discovered_info.as_dict if self._discovered_info is not None else None
            },
        )

    async def _async_get_device_from_discovered(
        self, discovered: DiscoveredDevice, config: dict[str, Any]
    ) -> TapoDevice:
        return await self._async_get_device(config | {CONF_HOST: discovered.ip}, discovered)

    async def _async_get_device(
            self,
            config: dict[str, Any],
            discovered_device: DiscoveredDevice | None = None,
    ) -> TapoDevice:
        if not config[CONF_HOST]:
            raise InvalidHost
        try:
            session = create_aiohttp_session(self.hass)
            credential = AuthCredential(config[CONF_USERNAME], config[CONF_PASSWORD])
            if discovered_device is None:
                host, port = get_host_port(config[CONF_HOST])
                config = DeviceConnectConfiguration(
                    credentials=credential,
                    host=host,
                    port=port,
                )
                device = await connect(config=config, session=session)
            else:
                device = await discovered_device.get_tapo_device(credential, session)
            await device.update()
            return device
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


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self.config_entry.data | user_input
            )
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=step_options(self.config_entry),
        )


def is_supported_device(discovered_device: DiscoveredDevice) -> bool:
    model = discovered_device.device_model.lower()
    kind = discovered_device.device_type.upper()
    if kind == "SMART.IPCAMERA" or "CAMERA" in kind:
        _LOGGER.info("Found device model: %s, but type not supported %s", model, kind)
        return False
    return True
