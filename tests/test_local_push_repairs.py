"""Hub startup isolation and entry-scoped recovery notices."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo import async_remove_entry
from custom_components.tapo.hub.hass_tapo_hub import HassTapoHub
from custom_components.tapo.hub.local_push import LocalPushManager
from custom_components.tapo.hub.local_push_repairs import (
    ISSUE_TYPES,
    async_set_push_issue,
)
from tests.conftest import mock_hub

A, B = "A" * 40, "B" * 40


def setup_hub(hass, monkeypatch, data):
    entry = MockConfigEntry(domain="tapo", title="Test H100", data=data, version=8)
    entry.add_to_hass(hass)
    hub = mock_hub()
    hub.model = "H100"
    hub.children = [
        SimpleNamespace(model="S200D", device_id=A, nickname="Knob"),
        SimpleNamespace(model="T310", device_id="sensor", nickname="Sensor"),
    ]
    coordinators = [SimpleNamespace(device=child) for child in hub.children]
    hass.data["tapo"] = {
        entry.entry_id: SimpleNamespace(
            device=hub, local_push=None, child_coordinators=coordinators
        )
    }
    wrapper = HassTapoHub(entry, hub)
    return entry, wrapper, coordinators


@pytest.mark.parametrize("failure", ["invalid_address", "removed_knob"])
async def test_push_problem_does_not_block_other_hub_platforms(
    hass, monkeypatch, failure
):
    data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "secret",
        "local_push_host": "not-an-ip" if failure == "invalid_address" else "127.0.0.1",
        "local_push_device_ids": [A, B],
    }
    entry, wrapper, coordinators = setup_hub(hass, monkeypatch, data)
    monkeypatch.setattr(
        HassTapoHub, "setup_children", AsyncMock(return_value=coordinators)
    )
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.TapoDataCoordinator",
        lambda *args: SimpleNamespace(async_config_entry_first_refresh=AsyncMock()),
    )
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.device_registry.async_get",
        lambda *args: MagicMock(),
    )
    forward = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward)
    if failure == "removed_knob":
        push = MagicMock(status="starting", async_start=AsyncMock())
        factory = MagicMock(return_value=push)
        monkeypatch.setattr(
            "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager", factory
        )
    assert await wrapper.initialize_hub(hass)
    forward.assert_awaited_once()
    assert coordinators[0]._local_push_managed
    assert coordinators[0]._local_push_selected
    assert not coordinators[1]._local_push_managed
    registry = ir.async_get(hass)
    assert registry.async_get_issue(
        "tapo", f"local_push_missing_devices_{entry.entry_id}"
    )
    if failure == "invalid_address":
        assert coordinators[0]._local_push is None
        assert registry.async_get_issue(
            "tapo", f"local_push_unavailable_{entry.entry_id}"
        )
    else:
        assert factory.call_args.args[3] == {A}
        assert not registry.async_get_issue(
            "tapo", f"local_push_unavailable_{entry.entry_id}"
        )


async def test_upgrade_notice_is_cleared_by_saving_configuration(hass, monkeypatch):
    data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "secret",
        "local_push_host": "127.0.0.1",
    }
    entry, wrapper, coordinators = setup_hub(hass, monkeypatch, data)
    push = MagicMock(status="starting", async_start=AsyncMock())
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager", lambda *args: push
    )
    await wrapper._async_setup_local_push(hass, coordinators)
    registry = ir.async_get(hass)
    key = f"local_push_upgrade_{entry.entry_id}"
    issue = registry.async_get_issue("tapo", key)
    assert issue is not None and issue.is_persistent
    await wrapper._async_setup_local_push(hass, coordinators)
    assert len([key for domain, key in registry.issues if domain == "tapo"]) == 1
    monkeypatch.setattr(
        "custom_components.tapo.config_flow.async_validate_push",
        AsyncMock(return_value={}),
    )
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    saved = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"host": data["host"], "local_push_device_ids": [A]}
    )
    assert saved["type"] == "create_entry"
    assert registry.async_get_issue("tapo", key) is None
    await wrapper._async_setup_local_push(hass, coordinators)
    assert registry.async_get_issue("tapo", key) is None


async def test_transport_failure_notice_clears_on_recovery(hass, monkeypatch):
    data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "secret",
        "local_push_host": "127.0.0.1",
        "local_push_device_ids": [A],
    }
    entry, wrapper, coordinators = setup_hub(hass, monkeypatch, data)
    push = LocalPushManager(hass, entry, wrapper.hub, {A}, "127.0.0.1", 18080)
    push.async_start = AsyncMock()
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager", lambda *args: push
    )
    await wrapper._async_setup_local_push(hass, coordinators)
    key = f"local_push_unavailable_{entry.entry_id}"
    registry = ir.async_get(hass)
    push._set_status("error", "RuntimeError")
    assert registry.async_get_issue("tapo", key)
    push._set_status("connecting")
    assert registry.async_get_issue("tapo", key)
    push._set_status("connected")
    assert registry.async_get_issue("tapo", key) is None


async def test_removed_knob_stays_configurable_and_notice_can_clear(hass, monkeypatch):
    data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "secret",
        "local_push_host": "127.0.0.1",
        "local_push_device_ids": [A, B],
    }
    entry, wrapper, coordinators = setup_hub(hass, monkeypatch, data)
    push = MagicMock(status="starting", async_start=AsyncMock())
    monkeypatch.setattr(
        "custom_components.tapo.hub.hass_tapo_hub.LocalPushManager", lambda *args: push
    )
    await wrapper._async_setup_local_push(hass, coordinators)
    key = f"local_push_missing_devices_{entry.entry_id}"
    assert ir.async_get(hass).async_get_issue("tapo", key)
    monkeypatch.setattr(
        "custom_components.tapo.config_flow.async_validate_push",
        AsyncMock(return_value={}),
    )
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    field = flow["data_schema"].schema
    selector = next(
        value
        for option, value in field.items()
        if option.schema == "local_push_device_ids"
    )
    assert {choice["value"] for choice in selector.config["options"]} == {A, B}
    await hass.config_entries.options.async_configure(
        flow["flow_id"], {"host": data["host"], "local_push_device_ids": [A]}
    )
    await wrapper._async_setup_local_push(hass, coordinators)
    assert ir.async_get(hass).async_get_issue("tapo", key) is None


async def test_entry_removal_only_clears_its_own_notices(hass):
    entries = [
        MockConfigEntry(domain="tapo", title=f"Hub {index}") for index in range(2)
    ]
    for entry in entries:
        for issue_type in ISSUE_TYPES:
            async_set_push_issue(hass, entry, issue_type, True)
    await async_remove_entry(hass, entries[0])
    registry = ir.async_get(hass)
    for issue_type in ISSUE_TYPES:
        assert (
            registry.async_get_issue("tapo", f"{issue_type}_{entries[0].entry_id}")
            is None
        )
        assert (
            registry.async_get_issue("tapo", f"{issue_type}_{entries[1].entry_id}")
            is not None
        )
