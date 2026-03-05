import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from plugp100.common.functional.tri import Success
from plugp100.new.child.tapohubchildren import TriggerButtonDevice
from plugp100.responses.hub_childs.s200b_device_state import (
    RotationEvent,
    SingleClickEvent,
)

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.hub.event import (
    EVENT_ROTATION,
    EVENT_SINGLE_CLICK,
    TapoButtonEvent,
    TapoDialEvent,
    _do_fetch,
    _get_hub_lock,
    fetch_event_logs,
)
from tests.conftest import _mock_hub_child_device


def _mock_trigger_device():
    device = _mock_hub_child_device(MagicMock(auto_spec=TriggerButtonDevice))
    logs = MagicMock()
    logs.events = []
    device.get_event_logs = AsyncMock(return_value=Success(logs))
    return device, logs


class TestGetHubLock:
    def test_creates_lock_on_first_call(self):
        hass_data = {}
        hass = MagicMock()
        hass.data = hass_data
        lock = _get_hub_lock(hass, "entry_1")
        assert isinstance(lock, asyncio.Lock)
        assert "tapo_hub_event_lock_entry_1" in hass_data

    def test_returns_same_lock_on_subsequent_calls(self):
        hass = MagicMock()
        hass.data = {}
        lock1 = _get_hub_lock(hass, "entry_1")
        lock2 = _get_hub_lock(hass, "entry_1")
        assert lock1 is lock2

    def test_different_entries_get_different_locks(self):
        hass = MagicMock()
        hass.data = {}
        lock1 = _get_hub_lock(hass, "entry_1")
        lock2 = _get_hub_lock(hass, "entry_2")
        assert lock1 is not lock2


class TestFetchEventLogs:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, self.logs = _mock_trigger_device()
        # Clear any cache
        if hasattr(self.coordinator, "_event_log_cache"):
            del self.coordinator._event_log_cache
        self.coordinator._event_log_cache = None

    async def test_fetches_from_device(self):
        logs, latency = await fetch_event_logs(self.coordinator, self.device)
        self.device.get_event_logs.assert_called_once_with(page_size=5, start_id=0)
        assert logs is self.logs
        assert latency >= 0

    async def test_returns_cached_result_within_validity_window(self):
        # First call populates cache
        await fetch_event_logs(self.coordinator, self.device)
        # Second call should hit cache
        await fetch_event_logs(self.coordinator, self.device)
        # Only one actual HTTP call
        self.device.get_event_logs.assert_called_once()

    async def test_cache_expires_after_validity_window(self):
        await fetch_event_logs(self.coordinator, self.device)
        # Expire the cache
        self.coordinator._event_log_cache["timestamp"] = time.monotonic() - 1.0
        await fetch_event_logs(self.coordinator, self.device)
        assert self.device.get_event_logs.call_count == 2

    async def test_uses_hub_lock_when_provided(self):
        hass = MagicMock()
        hass.data = {}
        await fetch_event_logs(
            self.coordinator, self.device, hass=hass, entry_id="entry_1"
        )
        assert "tapo_hub_event_lock_entry_1" in hass.data

    async def test_works_without_lock(self):
        logs, latency = await fetch_event_logs(self.coordinator, self.device)
        assert logs is self.logs

    async def test_custom_page_size(self):
        await fetch_event_logs(self.coordinator, self.device, page_size=10)
        self.device.get_event_logs.assert_called_once_with(page_size=10, start_id=0)

    async def test_records_latency_in_cache(self):
        await fetch_event_logs(self.coordinator, self.device)
        cache = self.coordinator._event_log_cache
        assert "timestamp" in cache
        assert "logs" in cache
        assert "latency_ms" in cache
        assert cache["latency_ms"] >= 0


class TestDoFetch:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, self.logs = _mock_trigger_device()
        self.coordinator._event_log_cache = None

    async def test_rechecks_cache_inside_lock(self):
        # Simulate another device having just populated the cache
        self.coordinator._event_log_cache = {
            "timestamp": time.monotonic(),
            "logs": self.logs,
            "latency_ms": 50.0,
        }
        logs, latency = await _do_fetch(self.coordinator, self.device, 5)
        # Should return cached result without calling device
        self.device.get_event_logs.assert_not_called()
        assert latency == 50.0


class TestTapoButtonEvent:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.entity = TapoButtonEvent(
            coordinator=self.coordinator, device=self.device
        )

    def test_unique_id(self):
        assert self.entity.unique_id == "123_button_event"

    def test_name(self):
        assert self.entity._attr_name == "Button Event"

    def test_event_types(self):
        assert self.entity._attr_event_types == [EVENT_SINGLE_CLICK]

    def test_handle_single_click_event(self):
        self.entity._trigger_event = MagicMock()
        self.entity.async_write_ha_state = MagicMock()
        event = MagicMock(spec=SingleClickEvent)
        event.__class__ = SingleClickEvent
        self.entity._handle_event(event)
        self.entity._trigger_event.assert_called_once_with(EVENT_SINGLE_CLICK)

    def test_ignores_rotation_event(self):
        self.entity._trigger_event = MagicMock()
        event = MagicMock(spec=RotationEvent)
        event.__class__ = RotationEvent
        self.entity._handle_event(event)
        self.entity._trigger_event.assert_not_called()


class TestTapoDialEvent:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.entity = TapoDialEvent(
            coordinator=self.coordinator, device=self.device
        )

    def test_unique_id(self):
        assert self.entity.unique_id == "123_dial_event"

    def test_name(self):
        assert self.entity._attr_name == "Dial Event"

    def test_event_types(self):
        assert self.entity._attr_event_types == [EVENT_ROTATION]

    def test_handle_rotation_event(self):
        self.entity._trigger_event = MagicMock()
        self.entity.async_write_ha_state = MagicMock()
        event = MagicMock(spec=RotationEvent)
        event.__class__ = RotationEvent
        event.degrees = 45
        self.entity._handle_event(event)
        self.entity._trigger_event.assert_called_once_with(
            EVENT_ROTATION, {"degrees": 45}
        )

    def test_ignores_single_click_event(self):
        self.entity._trigger_event = MagicMock()
        event = MagicMock(spec=SingleClickEvent)
        event.__class__ = SingleClickEvent
        self.entity._handle_event(event)
        self.entity._trigger_event.assert_not_called()


class TestTapoEventBaseStartupDeferral:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.device, _ = _mock_trigger_device()
        self.entity = TapoButtonEvent(
            coordinator=self.coordinator, device=self.device
        )

    def test_ha_started_defaults_false(self):
        assert self.entity._ha_started is False

    def test_handle_coordinator_update_skips_when_not_started(self):
        self.entity.hass = MagicMock()
        self.entity.async_write_ha_state = MagicMock()
        self.entity._handle_coordinator_update()
        self.entity.hass.async_create_task.assert_not_called()

    def test_handle_coordinator_update_runs_when_started(self):
        self.entity._ha_started = True
        self.entity.hass = MagicMock()
        self.entity.async_write_ha_state = MagicMock()
        self.entity._handle_coordinator_update()
        self.entity.hass.async_create_task.assert_called_once()

    def test_on_ha_started_callback(self):
        self.entity._on_ha_started(None)
        assert self.entity._ha_started is True


class TestPollAndFireEvents:
    @pytest.fixture(autouse=True)
    def init_data(self):
        self.coordinator = Mock(TapoDataCoordinator)
        self.coordinator._hub_entry_id = "entry_1"
        self.coordinator._event_log_cache = None
        self.device, self.logs = _mock_trigger_device()
        self.entity = TapoButtonEvent(
            coordinator=self.coordinator, device=self.device
        )
        self.entity.hass = MagicMock()
        self.entity._ha_started = True
        self.entity._trigger_event = MagicMock()
        self.entity.async_write_ha_state = MagicMock()

    async def test_first_poll_seeds_last_event_id(self):
        event = MagicMock(spec=SingleClickEvent)
        event.__class__ = SingleClickEvent
        event.id = 100
        self.logs.events = [event]
        await self.entity._poll_and_fire_events()
        assert self.entity._last_event_id == 100
        # First poll should NOT fire event (just seeds)
        self.entity._trigger_event.assert_not_called()

    async def test_new_event_fires(self):
        # Seed
        event1 = MagicMock(spec=SingleClickEvent)
        event1.__class__ = SingleClickEvent
        event1.id = 100
        self.logs.events = [event1]
        await self.entity._poll_and_fire_events()

        # Expire cache
        self.coordinator._event_log_cache["timestamp"] = time.monotonic() - 1.0

        # New event
        event2 = MagicMock(spec=SingleClickEvent)
        event2.__class__ = SingleClickEvent
        event2.id = 101
        self.logs.events = [event2, event1]
        await self.entity._poll_and_fire_events()
        self.entity._trigger_event.assert_called_once_with(EVENT_SINGLE_CLICK)

    async def test_same_event_id_does_not_fire(self):
        event = MagicMock(spec=SingleClickEvent)
        event.__class__ = SingleClickEvent
        event.id = 100
        self.logs.events = [event]
        await self.entity._poll_and_fire_events()

        # Expire cache
        self.coordinator._event_log_cache["timestamp"] = time.monotonic() - 1.0

        # Same event
        await self.entity._poll_and_fire_events()
        self.entity._trigger_event.assert_not_called()

    async def test_empty_events_does_nothing(self):
        self.logs.events = []
        await self.entity._poll_and_fire_events()
        assert self.entity._last_event_id is None

    async def test_fetch_exception_is_handled(self):
        self.device.get_event_logs = AsyncMock(side_effect=Exception("timeout"))
        # Should not raise
        await self.entity._poll_and_fire_events()
