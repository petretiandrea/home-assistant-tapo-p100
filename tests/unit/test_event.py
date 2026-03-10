from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.event import async_setup_entry


class TestEventPlatformSetup:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.hass = MagicMock()
        self.entry = MagicMock()
        self.entry.entry_id = "test_entry"
        self.async_add_entities = MagicMock()

    async def test_delegates_to_hub_event_when_is_hub(self):
        data = MagicMock()
        data.coordinator.is_hub = True
        self.hass.data = {"tapo": {"test_entry": data}}

        with patch(
            "custom_components.tapo.event.async_setup_hub_event",
            new_callable=AsyncMock,
        ) as mock_hub_setup:
            await async_setup_entry(self.hass, self.entry, self.async_add_entities)
            mock_hub_setup.assert_called_once_with(
                self.hass, self.entry, self.async_add_entities
            )

    async def test_does_not_delegate_when_not_hub(self):
        data = MagicMock()
        data.coordinator.is_hub = False
        self.hass.data = {"tapo": {"test_entry": data}}

        with patch(
            "custom_components.tapo.event.async_setup_hub_event",
            new_callable=AsyncMock,
        ) as mock_hub_setup:
            await async_setup_entry(self.hass, self.entry, self.async_add_entities)
            mock_hub_setup.assert_not_called()
