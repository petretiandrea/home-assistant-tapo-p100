"""Local push source isolation and protection of unrelated hub rules."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import CoreState
import pytest

from custom_components.tapo.hub.local_push import (
    CONF_LOCAL_PUSH_LEGACY_DEGREES,
    EVENT_LOCAL_PUSH,
    LocalPushManager,
)

FIXTURES = Path(__file__).parents[2] / "fixtures"


@pytest.fixture
def manager(monkeypatch):
    store = MagicMock()
    store.async_save = AsyncMock()
    monkeypatch.setattr(
        "custom_components.tapo.hub.local_push.Store", lambda *a, **kw: store
    )
    hass = MagicMock()
    hass.state = CoreState.running
    entry = SimpleNamespace(entry_id="test", data={"host": "192.0.2.1"})
    value = LocalPushManager(
        hass,
        entry,
        SimpleNamespace(model="H100"),
        {"A" * 40, "B" * 40},
        "127.0.0.1",
        18080,
    )
    value._state = {"receiver_id": "F" * 40, "rules": []}
    value._routes = {
        "06ef2": {"id": "R2f06ef2", "device_id": "A" * 40, "gesture": "single_click"},
        "f6135": {"id": "Rccf6135", "device_id": "A" * 40, "gesture": "positive"},
        "a7182": {"id": "R8ea7182", "device_id": "B" * 40, "gesture": "negative"},
    }
    value._set_status("connected")
    return value


def test_captured_commands_preserve_source_direction_and_amount(manager):
    fixture = json.loads((FIXTURES / "h100_local_push.json").read_text())
    for command in fixture["commands"]:
        manager._on_action(command)
    calls = manager.hass.bus.async_fire.call_args_list
    assert len(calls) == len(fixture["commands"])
    for call, command in zip(calls, fixture["commands"], strict=True):
        name, event = call.args
        assert name == EVENT_LOCAL_PUSH
        assert event["device_id"] == (
            "B" * 40 if command["method"] == "decrease_brightness" else "A" * 40
        )
        assert event["transport"] == "local_push"
        assert "degrees" not in event
        if command["method"] != "reverse_status":
            assert event["amount"] == command["params"]["delta"]
            assert event["signed_amount"] == event["amount"] * (
                -1 if event["device_id"] == "B" * 40 else 1
            )


@pytest.mark.parametrize("compatibility", [None, False, True])
def test_legacy_degrees_is_opt_in_and_preserves_native_amount(manager, compatibility):
    data = dict(manager.entry.data)
    if compatibility is not None:
        data[CONF_LOCAL_PUSH_LEGACY_DEGREES] = compatibility
    configured = LocalPushManager(
        manager.hass,
        SimpleNamespace(entry_id="configured", data=data),
        manager.hub,
        manager.device_ids,
        manager.host,
        manager.port,
    )
    configured._routes = manager._routes
    configured._set_status("connected")
    configured._on_action(
        {
            "method": "increase_brightness",
            "params": {"delta": 17},
            "action_dedup_id": "LC6abcdef6135TRG011234567",
        }
    )
    event = manager.hass.bus.async_fire.call_args.args[1]
    assert event["signed_amount"] == 17
    assert event["direction"] == "clockwise"
    if compatibility:
        assert event["degrees"] == 60
    else:
        assert "degrees" not in event


@pytest.mark.parametrize(
    "sample",
    json.loads((FIXTURES / "h100_rotation_degrees.json").read_text())["samples"],
    ids=lambda sample: str(sample["raw_degrees"]),
)
def test_recorded_rotations_preserve_legacy_degrees(manager, sample):
    manager.legacy_degrees = True
    token = "f6135" if sample["raw_degrees"] > 0 else "a7182"
    manager._on_action(
        {
            "method": sample["method"],
            "params": {"delta": sample["delta"]},
            "action_dedup_id": f"LC6abcde{token}TRG011234567",
        }
    )
    event = manager.hass.bus.async_fire.call_args.args[1]
    assert event["event_type"] == "rotation"
    assert event["degrees"] == sample["raw_degrees"]
    assert type(event["degrees"]) is int
    assert event["amount"] == sample["delta"]
    assert event["signed_amount"] == sample["delta"] * (
        1 if sample["raw_degrees"] > 0 else -1
    )


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize(
    ("delta", "degrees"), [(67, 240), (75, 270), (84, 300), (92, 330), (100, 360)]
)
def test_rotation_lookup_arithmetic_extension_to_360_degrees(
    manager, sign, delta, degrees
):
    """These larger steps follow the formula; hardware evidence stops at 210."""
    manager.legacy_degrees = True
    token = "f6135" if sign > 0 else "a7182"
    manager._on_action(
        {
            "method": "increase_brightness" if sign > 0 else "decrease_brightness",
            "params": {"delta": delta},
            "action_dedup_id": f"LC6abcde{token}TRG011234567",
        }
    )
    event = manager.hass.bus.async_fire.call_args.args[1]
    assert event["degrees"] == sign * degrees
    assert event["signed_amount"] == sign * delta


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("delta", [1, 7, 8, 10, 16, 18, 99])
def test_unknown_rotation_delta_retains_native_data_without_guessing_degrees(
    manager, sign, delta
):
    manager.legacy_degrees = True
    token = "f6135" if sign > 0 else "a7182"
    manager._on_action(
        {
            "method": "increase_brightness" if sign > 0 else "decrease_brightness",
            "params": {"delta": delta},
            "action_dedup_id": f"LC6abcde{token}TRG011234567",
        }
    )
    event = manager.hass.bus.async_fire.call_args.args[1]
    assert event["event_type"] == "rotation"
    assert event["degrees"] is None
    assert event["amount"] == delta
    assert event["signed_amount"] == sign * delta
    assert event["direction"] == ("clockwise" if sign > 0 else "counterclockwise")


def test_push_dial_entity_preserves_legacy_degrees_and_clears_unknown_value(manager):
    from custom_components.tapo.hub.event import TapoDialEvent
    from tests.unit.hub.test_event import _mock_trigger_device

    manager.legacy_degrees = True
    device, _ = _mock_trigger_device()
    entity = TapoDialEvent(MagicMock(), device)
    entity._ha_started = True
    entity.async_write_ha_state = MagicMock()
    manager.subscribe("B" * 40, entity._handle_local_push)
    for index, (delta, degrees) in enumerate([(17, -60), (7, None), (9, -30)]):
        manager._on_action(
            {
                "method": "decrease_brightness",
                "params": {"delta": delta},
                "action_dedup_id": f"LC6abcdea7182TRG01{index:07d}",
            }
        )
        # Exercise the actual EventEntity state attributes used by old templates.
        assert entity.state_attributes["event_type"] == "rotation"
        assert entity.state_attributes["degrees"] == degrees
        assert entity.state_attributes["signed_amount"] == -delta
    assert entity.async_write_ha_state.call_count == 3
    manager.legacy_degrees = False
    manager._on_action(
        {
            "method": "decrease_brightness",
            "params": {"delta": 9},
            "action_dedup_id": "LC6abcdea7182TRG010000003",
        }
    )
    assert "degrees" not in entity.state_attributes
    assert entity.state_attributes["signed_amount"] == -9
    device.get_event_logs.assert_not_awaited()


@pytest.mark.parametrize("dedup", [None, "", "LC6", "LC6abcdeZZZZZTRG011234567"])
def test_missing_or_unknown_source_never_fires(manager, dedup):
    manager._on_action(
        {"method": "reverse_status", "params": {}, "action_dedup_id": dedup}
    )
    manager.hass.bus.async_fire.assert_not_called()


def test_wrong_method_for_known_source_is_rejected(manager):
    manager._on_action(
        {
            "method": "reverse_status",
            "params": {},
            "action_dedup_id": "LC6Kf4aCf6135e514e2454040",
        }
    )
    manager.hass.bus.async_fire.assert_not_called()


def test_same_action_replayed_after_new_session_fires_once(manager):
    action = {
        "method": "reverse_status",
        "params": {},
        "action_dedup_id": "LC6kWO3h06ef25c2612454042",
    }
    manager._on_action(action)
    manager._on_action(deepcopy(action))
    assert manager.hass.bus.async_fire.call_count == 1


def test_no_startup_replay(manager):
    manager.hass.state = CoreState.starting
    manager._on_action(
        {
            "method": "reverse_status",
            "params": {},
            "action_dedup_id": "LC6kWO3h06ef25c2612454042",
        }
    )
    manager.hass.bus.async_fire.assert_not_called()


def test_captured_native_rule_is_owned_but_changed_target_is_not(manager):
    native = json.loads((FIXTURES / "h100_native_rules.json").read_text())[0]
    rule = manager._routes["06ef2"]
    assert manager._owns_native_rule(rule, native)
    changed = deepcopy(native)
    changed["action_setting_list"][0]["device_id"] = "E" * 40
    assert not manager._owns_native_rule(rule, changed)


async def test_conflicting_rule_is_never_deleted(manager):
    rule = manager._routes["06ef2"]
    native = json.loads((FIXTURES / "h100_native_rules.json").read_text())[0]
    native["action_setting_list"][0]["service"]["id"] = "someOtherService"
    manager._query = AsyncMock()
    with pytest.raises(RuntimeError, match="refusing deletion"):
        await manager._delete_owned([rule], {rule["id"]: native})
    manager._query.assert_not_awaited()


async def test_stop_releases_resources_even_when_hub_is_offline(manager):
    manager._state["rules"] = [manager._routes["06ef2"]]
    manager._native_rules = AsyncMock(side_effect=TimeoutError)
    manager._session = MagicMock(closed=False)
    manager._session.close = AsyncMock()
    manager._runner = MagicMock()
    manager._runner.cleanup = AsyncMock()
    await manager.async_stop()
    manager._runner.cleanup.assert_awaited_once()
    manager._session.close.assert_awaited_once()
    assert manager.status == "stopped"


async def test_reconciliation_persists_before_writes_and_reuses_rules(manager):
    """An interrupted creation remains attributable, and reload is idempotent."""
    manager.device_ids = {"A" * 40}
    manager._state["rules"] = [manager._routes["06ef2"]]
    fixture = json.loads((FIXTURES / "h100_native_rules.json").read_text())
    native = {}
    writes = []

    async def query(obj, method, params):
        assert obj == "action_manager"
        if method == "debug":
            return {"sum": len(native), "rule_content_list": list(native.values())}
        if method == "update_rule":
            identifier = params["smartPk"]["id"]
            # The most recent durable snapshot must already own the new ID.
            saved = manager._store.async_save.call_args.args[0]
            rule = next(r for r in saved["rules"] if r["id"] == identifier)
            template_index = (
                1
                if rule["gesture"] == "positive"
                else 2
                if rule["gesture"] == "negative"
                else 0
            )
            value = deepcopy(fixture[template_index])
            value.update(
                id=identifier, version=params["version"], enabled=params["enabled"]
            )
            value["trigger_team_list"][0]["event_list"][0].update(
                device_id=rule["device_id"],
                event_id="doubleClick"
                if rule["gesture"] == "double_click"
                else "singleClick"
                if rule["gesture"] == "single_click"
                else "rotation",
            )
            native[identifier] = value
            writes.append(deepcopy(params))
            return {}
        raise AssertionError(method)

    manager._query = AsyncMock(side_effect=query)
    await manager._reconcile()
    assert len(native) == 4
    assert len(writes) == 8  # Each rule is verified disabled before it is enabled.
    assert len(manager._routes) == 4
    first_ids = set(native)
    await manager._reconcile()
    assert set(native) == first_ids
    assert len(writes) == 8
    native_reader = manager._native_rules
    manager._native_rules = AsyncMock(side_effect=TimeoutError)
    with pytest.raises(TimeoutError):
        await manager._reconcile()
    assert manager._routes == {}
    manager._native_rules = native_reader
    await manager._reconcile()
    assert len(manager._routes) == 4
    assert set(native) == first_ids
    assert len(writes) == 8


async def test_changed_rule_source_invalidates_stale_attribution(manager):
    rule = manager._routes["f6135"]
    manager._state["rules"] = [rule]
    native = json.loads((FIXTURES / "h100_native_rules.json").read_text())[1]
    native["trigger_team_list"][0]["event_list"][0]["device_id"] = "B" * 40
    manager._native_rules = AsyncMock(return_value={rule["id"]: native})
    manager._query = AsyncMock()
    with pytest.raises(RuntimeError, match="Rule ID conflict"):
        await manager._reconcile()
    assert manager._routes == {}
    manager._query.assert_not_awaited()
    manager._on_action(
        {
            "method": "increase_brightness",
            "params": {"delta": 9},
            "action_dedup_id": "LC6abcdef6135TRG011234567",
        }
    )
    manager.hass.bus.async_fire.assert_not_called()


@pytest.mark.parametrize("status", ["starting", "connecting", "error", "stopped"])
def test_unavailable_push_never_emits_using_retained_routes(manager, status):
    manager._set_status(status)
    manager._on_action(
        {
            "method": "reverse_status",
            "params": {},
            "action_dedup_id": "LC6abcde06ef2TRG011234567",
        }
    )
    manager.hass.bus.async_fire.assert_not_called()


async def test_background_bind_failure_retries_and_recovers(manager):
    states = []
    manager.subscribe_status(lambda: states.append((manager.status, manager.available)))
    routes = dict(manager._routes)
    manager._runner = manager._transport = None
    attempts = 0

    async def bind():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("port busy")
        manager._runner = manager._transport = MagicMock()

    async def reconcile():
        manager._routes = routes

    waits = 0

    async def wait():
        nonlocal waits
        waits += 1
        if waits == 1:
            assert manager._routes == {}
            assert not manager.available
        else:
            manager._stop.set()

    manager._async_bind = AsyncMock(side_effect=bind)
    manager._announce = MagicMock()
    manager._registered = AsyncMock(return_value=True)
    manager._reconcile = AsyncMock(side_effect=reconcile)
    manager._stop.wait = AsyncMock(side_effect=wait)
    await manager._run()
    assert attempts == 2
    assert states == [("error", False), ("connected", True)]
    assert manager._routes == routes


@pytest.mark.parametrize("failure", ["tcp", "discovery"])
async def test_partial_bind_releases_tcp_before_retry(manager, monkeypatch, failure):
    from custom_components.tapo.hub.local_receiver import DiscoveryResponder

    manager.hass.data = {}
    manager._receiver = MagicMock()
    manager._discovery = {"device_id": manager.receiver_id}
    runners = [MagicMock(setup=AsyncMock(), cleanup=AsyncMock()) for _ in range(2)]
    monkeypatch.setattr(
        "custom_components.tapo.hub.local_push.web.AppRunner",
        MagicMock(side_effect=runners),
    )
    start = AsyncMock(
        side_effect=[OSError("busy"), None] if failure == "tcp" else [None, None]
    )
    monkeypatch.setattr(
        "custom_components.tapo.hub.local_push.web.TCPSite",
        lambda *a, **kw: SimpleNamespace(start=start),
    )
    responder = DiscoveryResponder()
    responder.connection_made(MagicMock())
    endpoints = [(responder.transport, responder)]
    if failure == "discovery":
        endpoints.insert(0, OSError("busy"))
    manager.hass.loop.create_datagram_endpoint = AsyncMock(side_effect=endpoints)
    with pytest.raises(OSError):
        await manager._async_bind()
    assert not manager.listening
    runners[0].cleanup.assert_awaited_once()
    await manager._async_bind()
    assert manager.listening
    assert manager._runner is runners[1]
    assert responder.devices[manager.hub_host] == manager._discovery
    await manager.async_stop()
    runners[1].cleanup.assert_awaited_once()


async def test_event_availability_tracks_transport_and_recovers_without_polling(
    hass, manager, monkeypatch
):
    from custom_components.tapo.hub.event import TapoDialEvent
    from tests.unit.hub.test_event import _mock_trigger_device

    device, _ = _mock_trigger_device()
    coordinator = MagicMock(last_update_success=True)
    coordinator._local_push_managed = True
    coordinator._local_push = manager
    entity = TapoDialEvent(coordinator, device)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    poller = MagicMock(side_effect=AssertionError("Push cannot fall back to polling"))
    monkeypatch.setattr(
        "custom_components.tapo.hub.event.get_hub_event_log_poller", poller
    )
    await entity.async_added_to_hass()
    assert entity.available
    manager._set_status("error", "RuleConflict")
    assert not entity.available
    manager._set_status("connected")
    assert entity.available
    assert entity.async_write_ha_state.call_count == 2
    coordinator.last_update_success = False
    assert not entity.available
    poller.assert_not_called()
    device.get_event_logs.assert_not_awaited()


async def test_selected_knob_without_receiver_is_unavailable_and_never_polls(
    hass, monkeypatch
):
    from plugp100.devices.children.trigger_button import TriggerButtonDevice

    from custom_components.tapo.hub.event import async_setup_entry
    from tests.unit.hub.test_event import _mock_trigger_device

    device, _ = _mock_trigger_device()
    device.__class__ = TriggerButtonDevice
    device.has_component = MagicMock(return_value=True)
    coordinator = MagicMock(device=device, last_update_success=True)
    coordinator._local_push_managed = coordinator._local_push_selected = True
    coordinator._local_push = None
    hass.data["tapo"] = {"test": SimpleNamespace(child_coordinators=[coordinator])}
    add = MagicMock()
    await async_setup_entry(hass, SimpleNamespace(entry_id="test"), add)
    entities = add.call_args.args[0]
    assert len(entities) == 2
    poller = MagicMock(side_effect=AssertionError("No polling when receiver fails"))
    monkeypatch.setattr(
        "custom_components.tapo.hub.event.get_hub_event_log_poller", poller
    )
    for entity in entities:
        entity.hass = hass
        entity.async_write_ha_state = MagicMock()
        assert not entity.available
        await entity.async_added_to_hass()
        entity._ha_started = True
        entity._handle_coordinator_update()
    poller.assert_not_called()
    device.get_event_logs.assert_not_awaited()


async def test_incomplete_snapshot_and_suffix_conflict_refuse_writes(manager):
    rule = manager._routes["06ef2"]
    manager._query = AsyncMock(return_value={"sum": 2, "rule_content_list": []})
    with pytest.raises(RuntimeError, match="Incomplete"):
        await manager._reconcile()
    assert manager._query.await_count == 1
    manager._state["rules"] = [rule]
    manager._native_rules = AsyncMock(return_value={"other06ef2": {"id": "other06ef2"}})
    manager._query.reset_mock()
    with pytest.raises(RuntimeError, match="Ambiguous"):
        await manager._reconcile()
    manager._query.assert_not_awaited()


async def test_only_retired_owned_rules_are_deleted(manager):
    native = json.loads((FIXTURES / "h100_native_rules.json").read_text())
    rule = manager._routes["06ef2"]
    manager._query = AsyncMock()
    await manager._delete_owned([rule], {r["id"]: r for r in native})
    manager._query.assert_awaited_once_with(
        "action_manager", "delete_rule", {"delete_list": [{"id": rule["id"]}]}
    )


def test_listener_failure_does_not_prevent_other_consumers(manager):
    broken = MagicMock(side_effect=RuntimeError("listener failure"))
    listener = MagicMock()
    manager.subscribe("A" * 40, broken)
    manager.subscribe("A" * 40, listener)
    manager.subscribe_status(broken)
    manager._on_action(
        {
            "method": "reverse_status",
            "params": {},
            "action_dedup_id": "LC6kWO3h06ef25c2612454042",
        }
    )
    listener.assert_called_once()
    manager.hass.bus.async_fire.assert_called_once()


def test_push_does_not_hide_a_reconciliation_error(manager):
    manager._set_status("error", "RuleConflict")
    manager._on_action(
        {
            "method": "reverse_status",
            "params": {},
            "action_dedup_id": "LC6kWO3h06ef25c2612454042",
        }
    )
    assert manager.status == "error"
    assert manager.last_error == "RuleConflict"


async def test_multiple_hubs_share_discovery_and_release_last_socket(hass, monkeypatch):
    """Unloading one H100 must not disconnect another H100 on the same host."""
    from custom_components.tapo.hub.local_push import DISCOVERY_KEY
    from custom_components.tapo.hub.local_receiver import DiscoveryResponder

    responder = DiscoveryResponder()
    transport = MagicMock()
    responder.connection_made(transport)
    endpoint = AsyncMock(return_value=(transport, responder))
    monkeypatch.setattr(hass.loop, "create_datagram_endpoint", endpoint)
    site = MagicMock()
    site.start = AsyncMock()
    monkeypatch.setattr(
        "custom_components.tapo.hub.local_push.web.TCPSite", lambda *a, **kw: site
    )
    managers = []
    for index in range(2):
        entry = SimpleNamespace(
            entry_id=str(index),
            data={
                "host": f"192.0.2.{index + 1}",
                "username": "user",
                "password": "test-secret",
            },
        )
        value = LocalPushManager(
            hass,
            entry,
            SimpleNamespace(model="H100"),
            {"A" * 40},
            "127.0.0.1",
            18080 + index,
        )
        value._store = SimpleNamespace(
            async_load=AsyncMock(return_value={}), async_save=AsyncMock()
        )
        value._run = AsyncMock()
        value._native_rules = AsyncMock(return_value={})
        await value.async_start()
        await value._async_bind()
        managers.append(value)
    await hass.async_block_till_done()
    assert endpoint.await_count == 1
    assert len(responder.devices) == 2
    await managers[0].async_stop()
    transport.close.assert_not_called()
    assert len(responder.devices) == 1
    # Even a failed withdrawal must release sockets/session resources.
    transport.sendto.side_effect = OSError("interface down")
    await managers[1].async_stop()
    transport.close.assert_called_once()
    assert hass.data[DISCOVERY_KEY] == {}
    assert all(value._session.closed for value in managers)


async def test_disabled_push_knob_has_no_event_poller_or_entities(manager):
    from custom_components.tapo.hub.event import async_setup_entry

    coordinator = SimpleNamespace(
        device=SimpleNamespace(), _local_push_managed=True, _local_push=None
    )
    hass = SimpleNamespace(
        data={"tapo": {"test": SimpleNamespace(child_coordinators=[coordinator])}}
    )
    add = MagicMock()
    await async_setup_entry(hass, SimpleNamespace(entry_id="test"), add)
    add.assert_not_called()


def test_push_entity_updates_never_schedule_event_logs(manager, monkeypatch):
    from custom_components.tapo.hub.event import TapoButtonEvent
    from tests.unit.hub.test_event import _mock_trigger_device

    device, _ = _mock_trigger_device()
    coordinator = MagicMock()
    coordinator._local_push = manager
    entity = TapoButtonEvent(coordinator, device)
    entity._ha_started = True
    entity.async_write_ha_state = MagicMock()
    poller = MagicMock(
        side_effect=AssertionError("Push must not create an event-log poller")
    )
    monkeypatch.setattr(
        "custom_components.tapo.hub.event.get_hub_event_log_poller", poller
    )
    entity._handle_coordinator_update()
    poller.assert_not_called()
    device.get_event_logs.assert_not_awaited()


@pytest.mark.parametrize("selection", [None, [], ["A" * 40]])
async def test_h100_defaults_to_push_and_deselection_never_enables_polling(
    hass, monkeypatch, selection
):
    from custom_components.tapo.hub.hass_tapo_hub import HassTapoHub

    children = [
        SimpleNamespace(model="S200D", device_id=value)
        for value in ["A" * 40, "B" * 40]
    ]
    hub = SimpleNamespace(model="H100", children=children)
    data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "test-secret",
        "local_push_host": "127.0.0.1",
    }
    if selection is not None:
        data["local_push_device_ids"] = selection
    entry = SimpleNamespace(entry_id="test", data=data, async_on_unload=MagicMock())
    coordinators = [SimpleNamespace(device=child) for child in children]
    state = SimpleNamespace(local_push=None)
    hass.data["tapo"] = {"test": state}
    push = MagicMock()
    push.async_start = AsyncMock()
    factory = MagicMock(return_value=push)
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager", factory
    )
    await HassTapoHub(entry, hub)._async_setup_local_push(hass, coordinators)
    expected = {"A" * 40, "B" * 40} if selection is None else set(selection)
    assert all(c._local_push_managed for c in coordinators)
    if expected:
        assert factory.call_args.args[3] == expected
        push.async_start.assert_awaited_once()
        assert state.local_push is push
    else:
        factory.assert_not_called()
    assert {
        c.device.device_id
        for c in coordinators
        if getattr(c, "_local_push", None) is push
    } == expected


async def test_push_setup_error_is_isolated_and_closes_partial_receiver(
    hass, monkeypatch
):
    from homeassistant.helpers import issue_registry as ir

    from custom_components.tapo.hub.hass_tapo_hub import HassTapoHub

    child = SimpleNamespace(model="S200D", device_id="A" * 40)
    hub = SimpleNamespace(model="H100", children=[child])
    entry = SimpleNamespace(
        entry_id="test",
        data={"host": "192.0.2.1", "local_push_host": "127.0.0.1"},
        async_on_unload=MagicMock(),
    )
    push = MagicMock(port=18080)
    push.async_start = AsyncMock(side_effect=OSError("port in use"))
    push.async_stop = AsyncMock()
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager",
        lambda *a, **kw: push,
    )
    hass.data["tapo"] = {"test": SimpleNamespace(local_push=None)}
    coordinator = SimpleNamespace(device=child)
    await HassTapoHub(entry, hub)._async_setup_local_push(hass, [coordinator])
    push.async_stop.assert_awaited_once()
    assert coordinator._local_push is push
    assert coordinator._local_push_selected
    assert ir.async_get(hass).async_get_issue("tapo", "local_push_unavailable_test")


@pytest.mark.parametrize("change", ["schedule", "future_action", "custom_action"])
def test_user_modified_rule_semantics_are_not_owned(manager, change):
    native = json.loads((FIXTURES / "h100_native_rules.json").read_text())[0]
    if change == "schedule":
        native["effective_periods"][0]["days_of_week"] = 1
    elif change == "future_action":
        native["action_setting_list"][0]["future_type"] = 1
    else:
        native["action_setting_list"][0]["action_id"] = "user-action"
    assert not manager._owns_native_rule(manager._routes["06ef2"], native)
