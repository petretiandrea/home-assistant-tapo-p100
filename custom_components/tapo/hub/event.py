import logging
import time
from typing import cast

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.new.child.tapohubchildren import TriggerButtonDevice
from plugp100.new.components.trigger_log_component import TriggerLogComponent
from plugp100.responses.hub_childs.s200b_device_state import (
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


async def fetch_event_logs(coordinator, device, page_size=5):
    """Fetch event logs with per-cycle caching on the coordinator.

    Returns (logs, latency_ms). The first caller in each update cycle
    does the actual HTTP request; subsequent callers get the cached result.
    """
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

    @callback
    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._poll_and_fire_events())
        self.async_write_ha_state()

    async def _poll_and_fire_events(self) -> None:
        try:
            logs, _ = await fetch_event_logs(self.coordinator, self._device)
        except Exception:
            _LOGGER.debug("Failed to fetch event logs for %s", self._device.device_id)
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
