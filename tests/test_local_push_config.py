"""Onboarding, validation, defaults, and disabling local events."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo.config_flow import TapoConfigFlow
from custom_components.tapo.const import DOMAIN
from custom_components.tapo.hub.local_push import async_validate_push

A = "A" * 40
CHOICES = [{"value": A, "label": "Test knob"}]
DATA = {"host": "192.0.2.1", "username": "user", "password": "secret"}


async def test_first_h100_setup_offers_push_with_all_knobs_selected(hass):
    device = SimpleNamespace(
        model="H100",
        nickname="Test hub",
        host=DATA["host"],
        mac="AA:BB:CC:DD:EE:FF",
        children=[SimpleNamespace(model="S200D", device_id=A, nickname="Test knob")],
    )
    with (
        patch.object(
            TapoConfigFlow, "_async_get_device", AsyncMock(return_value=device)
        ),
        patch("custom_components.tapo.async_setup_entry", AsyncMock(return_value=True)),
        patch(
            "custom_components.tapo.config_flow.async_validate_push",
            AsyncMock(return_value={}),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=DATA
        )
        assert result["step_id"] == "local_push"
        assert result["data_schema"]({})["local_push_device_ids"] == [A]
        final = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "local_push_device_ids": [A],
                "local_push_port": 18081,
                "local_push_host": "192.0.2.2",
            },
        )
        assert final["type"] == "create_entry"
        assert final["data"]["local_push_port"] == 18081
        assert final["data"]["local_push_device_ids"] == [A]
        assert final["data"]["password"] == DATA["password"]


async def test_options_errors_do_not_save_and_empty_selection_disables(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data=DATA | {"local_push_device_ids": [A]}, version=8
    )
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {
        entry.entry_id: SimpleNamespace(
            device=SimpleNamespace(model="H100"),
            child_coordinators=[
                SimpleNamespace(
                    device=SimpleNamespace(model="S200D", device_id=A, nickname="Knob")
                )
            ],
            local_push=None,
        )
    }
    result = await hass.config_entries.options.async_init(entry.entry_id)
    invalid = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "host": DATA["host"],
            "local_push_device_ids": [A],
            "local_push_host": "not-an-ip",
            "local_push_port": 18080,
        },
    )
    assert invalid["errors"] == {"local_push_host": "invalid_receiver_address"}
    assert entry.data["local_push_device_ids"] == [A]
    final = await hass.config_entries.options.async_configure(
        result["flow_id"], {"host": DATA["host"], "local_push_device_ids": []}
    )
    assert final["type"] == "create_entry"
    assert entry.data["local_push_device_ids"] == []
    assert entry.data["password"] == DATA["password"]


async def test_failed_entry_options_can_disable_without_live_device(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data=DATA | {"local_push_device_ids": [A]}, version=8
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "local_push_device_ids" in result["data_schema"]({"host": DATA["host"]})
    final = await hass.config_entries.options.async_configure(
        result["flow_id"], {"host": DATA["host"], "local_push_device_ids": []}
    )
    assert final["type"] == "create_entry"


async def test_unknown_knob_and_invalid_ip_are_actionable(hass):
    errors = await async_validate_push(
        hass, DATA | {"local_push_device_ids": ["B" * 40]}, CHOICES
    )
    assert errors == {"local_push_device_ids": "invalid_push_devices"}
    errors = await async_validate_push(
        hass,
        DATA | {"local_push_device_ids": [A], "local_push_host": "0.0.0.0"},
        CHOICES,
    )
    assert errors == {"local_push_host": "invalid_receiver_address"}


async def test_port_conflict_and_current_receiver_exemption(hass):
    data = DATA | {
        "local_push_device_ids": [A],
        "local_push_host": "127.0.0.1",
        "local_push_port": 18080,
    }
    with patch("custom_components.tapo.hub.local_push.socket.socket") as probe:
        probe.return_value.__enter__.return_value.bind.side_effect = OSError("in use")
        assert await async_validate_push(hass, data, CHOICES) == {
            "base": "receiver_unavailable"
        }
        # The existing receiver already owns both sockets; do not reject its settings.
        hass.data["tapo_local_push_discovery"] = {"127.0.0.1": object()}
        assert (
            await async_validate_push(
                hass,
                data,
                CHOICES,
                current=SimpleNamespace(host="127.0.0.1", port=18080),
            )
            == {}
        )
