import asyncio
from dataclasses import dataclass
import logging
import time
from typing import Callable, cast

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.components.trigger_log import TriggerLogComponent
from plugp100.devices.children.trigger_button import TriggerButtonDevice
from plugp100.models.hub_children.button import (
    RotationEvent,
    S200BEvent,
    SingleClickEvent,
)

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity

_LOGGER = logging.getLogger(__name__)

# Cache validity window — within the same update cycle, all entities
# reuse the same event log fetch instead of hitting the hub 3 times.
_CACHE_VALIDITY_S = 0.2


@dataclass
class EventLogPollResult:
    logs: object
    latency_ms: float


EventLogListener = Callable[[EventLogPollResult | None], None]


def _get_hub_lock(hass, entry_id):
    """Get or create a per-hub asyncio.Lock to serialize event log fetches.

    All child devices on the same hub share one lock so HTTP requests
    to the hub never overlap, which keeps latency low.
    """
    key = f"tapo_hub_event_lock_{entry_id}"
    lock = hass.data.get(key)
    if lock is None:
        lock = asyncio.Lock()
        hass.data[key] = lock
    return lock


async def fetch_event_logs(coordinator, device, page_size=5, hass=None, entry_id=None):
    """Fetch event logs with per-cycle caching on the coordinator.

    Returns (logs, latency_ms). The first caller in each update cycle
    does the actual HTTP request; subsequent callers get the cached result.
    A per-hub lock serializes requests across child devices.
    """
    cache = getattr(coordinator, "_event_log_cache", None)
    now = time.monotonic()

    if cache and (now - cache["timestamp"]) < _CACHE_VALIDITY_S:
        return cache["logs"], cache["latency_ms"]

    # Acquire hub-level lock if available
    lock = None
    if hass and entry_id:
        lock = _get_hub_lock(hass, entry_id)

    if lock:
        async with lock:
            return await _do_fetch(coordinator, device, page_size)
    else:
        return await _do_fetch(coordinator, device, page_size)


async def _do_fetch(coordinator, device, page_size):
    """Perform the actual HTTP fetch and update cache."""
    # Re-check cache inside the lock in case another device just fetched
    cache = getattr(coordinator, "_event_log_cache", None)
    now = time.monotonic()
    if cache and (now - cache["timestamp"]) < _CACHE_VALIDITY_S:
        return cache["logs"], cache["latency_ms"]

    start = now
    result = await device.get_event_logs(page_size=page_size, start_id=0)
    logs = result.get_or_raise()
    latency_ms = (time.monotonic() - start) * 1000

    coordinator._event_log_cache = {
        "timestamp": now,
        "logs": logs,
        "latency_ms": latency_ms,
    }

    return logs, latency_ms


class HubEventLogPoller:
    """Shared event-log poller for a trigger-button coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TapoDataCoordinator,
        device: TriggerButtonDevice,
        entry_id: str | None,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._device = device
        self._entry_id = entry_id
        self._listeners: set[EventLogListener] = set()
        self._task: asyncio.Task | None = None
        self._last_result: EventLogPollResult | None = None

    @property
    def last_result(self) -> EventLogPollResult | None:
        return self._last_result

    @callback
    def add_listener(self, listener: EventLogListener) -> Callable[[], None]:
        self._listeners.add(listener)

        def _remove_listener() -> None:
            self._listeners.discard(listener)

        return _remove_listener

    @callback
    def schedule_refresh(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = self._hass.async_create_task(self._async_refresh())

    async def _async_refresh(self) -> None:
        result: EventLogPollResult | None = None
        try:
            logs, latency_ms = await fetch_event_logs(
                self._coordinator,
                self._device,
                hass=self._hass,
                entry_id=self._entry_id,
            )
            result = EventLogPollResult(logs=logs, latency_ms=latency_ms)
        except Exception:
            _LOGGER.debug("Failed to fetch event logs for %s", self._device.device_id)

        self._last_result = result
        for listener in tuple(self._listeners):
            listener(result)


def get_hub_event_log_poller(
    hass: HomeAssistant,
    coordinator: TapoDataCoordinator,
    device: TriggerButtonDevice,
    entry_id: str | None,
) -> HubEventLogPoller:
    """Get or create the shared event-log poller for a child coordinator."""
    poller = getattr(coordinator, "_hub_event_log_poller", None)
    if poller is None:
        poller = HubEventLogPoller(hass, coordinator, device, entry_id)
        coordinator._hub_event_log_poller = poller
    return poller


EVENT_SINGLE_CLICK = "single_click"
EVENT_ROTATION = "rotation"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    for child_coordinator in data.child_coordinators:
        device = child_coordinator.device
        if isinstance(device, TriggerButtonDevice) and device.has_component(
            TriggerLogComponent
        ):
            async_add_entities(
                [
                    TapoButtonEvent(child_coordinator, device),
                    TapoDialEvent(child_coordinator, device),
                ],
                True,
            )


class _TapoEventBase(CoordinatedTapoEntity, EventEntity):
    """Base class that polls event logs and delegates to subclasses."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        device: TriggerButtonDevice,
    ) -> None:
        super().__init__(coordinator, device)
        self._device: TriggerButtonDevice = device
        self._last_event_id: int | None = None
        self._ha_started: bool = False
        self._event_log_poller: HubEventLogPoller | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._event_log_poller = get_hub_event_log_poller(
            self.hass,
            self.coordinator,
            self._device,
            getattr(self.coordinator, "_hub_entry_id", None),
        )
        self.async_on_remove(
            self._event_log_poller.add_listener(self._handle_event_log_result)
        )
        if self.hass.state is CoreState.running:
            self._ha_started = True
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._on_ha_started
            )

    @callback
    def _on_ha_started(self, _event) -> None:
        self._ha_started = True

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self._ha_started:
            return
        if self._event_log_poller is None:
            self._event_log_poller = get_hub_event_log_poller(
                self.hass,
                self.coordinator,
                self._device,
                getattr(self.coordinator, "_hub_entry_id", None),
            )
        self._event_log_poller.schedule_refresh()
        self.async_write_ha_state()

    @callback
    def _handle_event_log_result(self, result: EventLogPollResult | None) -> None:
        if result is None:
            return
        self._process_logs(result.logs)

    async def _poll_and_fire_events(self) -> None:
        try:
            logs, _ = await fetch_event_logs(
                self.coordinator,
                self._device,
                hass=self.hass,
                entry_id=getattr(self.coordinator, "_hub_entry_id", None),
            )
        except Exception:
            _LOGGER.debug("Failed to fetch event logs for %s", self._device.device_id)
            return

        self._process_logs(logs)

    def _process_logs(self, logs) -> None:
        if not self._ha_started:
            return

        if not logs.events:
            return

        latest = logs.events[0]
        event_id = latest.id

        if self._last_event_id is None:
            self._last_event_id = event_id
            return

        if event_id == self._last_event_id:
            return

        new_events: list[S200BEvent] = []
        for event in logs.events:
            if event.id == self._last_event_id:
                break
            new_events.append(event)

        self._last_event_id = event_id

        for event in reversed(new_events):
            self._handle_event(event)

    def _handle_event(self, event: S200BEvent) -> None:
        raise NotImplementedError


class TapoButtonEvent(_TapoEventBase):
    """Event entity for S200B/S200D button presses."""

    _attr_name = "Button Event"
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [EVENT_SINGLE_CLICK]

    @property
    def unique_id(self):
        return super().unique_id + "_button_event"

    def _handle_event(self, event: S200BEvent) -> None:
        if isinstance(event, SingleClickEvent):
            self._trigger_event(EVENT_SINGLE_CLICK)
            self.async_write_ha_state()


class TapoDialEvent(_TapoEventBase):
    """Event entity for S200B/S200D dial rotation."""

    _attr_name = "Dial Event"
    _attr_event_types = [EVENT_ROTATION]

    @property
    def unique_id(self):
        return super().unique_id + "_dial_event"

    def _handle_event(self, event: S200BEvent) -> None:
        if isinstance(event, RotationEvent):
            self._trigger_event(EVENT_ROTATION, {"degrees": event.degrees})
            self.async_write_ha_state()
