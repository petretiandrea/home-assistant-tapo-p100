import voluptuous as vol
from typing import Any
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_SCAN_INTERVAL
from custom_components.tapo.const import (
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DEFAULT_POLLING_RATE_S,
)
from custom_components.tapo.utils import get_entry_data  # pylint:disable=unused-import


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Manage the options."""
        entry_data = get_entry_data(self.config_entry)
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    description="Polling rate in seconds (e.g. 0.5 seconds means 500ms)",
                    default=entry_data.get(CONF_SCAN_INTERVAL, DEFAULT_POLLING_RATE_S),
                ): vol.All(vol.Coerce(float), vol.Clamp(min=1)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
