"""Authenticate against the receiver with plugp100's independent KLAP client."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiohttp import web
from plugp100.api.protocol.klap.klap_handshake_revision import KlapHandshakeRevisionV2
from plugp100.api.protocol.klap.klap_protocol import KlapChiper
from plugp100.common.credentials import AuthCredential
import pytest

from custom_components.tapo.hub.local_receiver import (
    DiscoveryResponder,
    VirtualReceiver,
    auth_hash,
    discovery_reply,
)


def request(body=b"", cookie=None, sequence=1):
    return SimpleNamespace(
        read=AsyncMock(return_value=body),
        cookies={"TP_SESSIONID": cookie} if cookie else {},
        query={"seq": str(sequence)},
    )


async def authenticated(receiver):
    seed = bytes(range(16))
    first = await receiver.handshake1(request(seed))
    cookie = first.cookies["TP_SESSIONID"].value
    server_seed = first.body[:16]
    strategy = KlapHandshakeRevisionV2()
    secret = strategy.generate_auth_hash(
        AuthCredential("user@example.com", "test-secret")
    )
    assert first.body[16:] == strategy.handshake1_seed_auth_hash(
        seed, server_seed, secret
    )
    await receiver.handshake2(
        request(strategy.handshake2_seed_auth_hash(seed, server_seed, secret), cookie)
    )
    return KlapChiper(seed, server_seed, secret), cookie


@pytest.fixture
def receiver():
    return VirtualReceiver(
        auth_hash("user@example.com", "test-secret"),
        "F" * 40,
        peer="192.0.2.1",
        on_action=MagicMock(),
    )


async def test_real_klap_client_authentication_encryption_and_exact_retry(receiver):
    cipher, cookie = await authenticated(receiver)
    payload, seq = cipher.encrypt(
        json.dumps(
            {
                "method": "increase_brightness",
                "params": {"delta": 9},
                "action_dedup_id": "LC6kWO3h06ef25c2612454042",
            }
        )
    )
    first = await receiver.request(request(payload, cookie, seq))
    assert json.loads(cipher.decrypt(first.body)) == {"error_code": 0, "result": {}}
    retry = await receiver.request(request(payload, cookie, seq))
    assert retry.body == first.body
    receiver.on_action.assert_called_once()
    assert receiver.on_action.call_args.args[0]["params"] == {"delta": 9}
    next_payload, next_seq = cipher.encrypt('{"method":"get_device_running_info"}')
    response = await receiver.request(request(next_payload, cookie, next_seq))
    assert json.loads(cipher.decrypt(response.body))["result"]["brightness"] == 59


async def test_bad_signature_and_sequence_cannot_emit(receiver):
    cipher, cookie = await authenticated(receiver)
    payload, seq = cipher.encrypt('{"method":"reverse_status"}')
    with pytest.raises(web.HTTPForbidden):
        await receiver.request(
            request(bytes([payload[0] ^ 1]) + payload[1:], cookie, seq)
        )
    await receiver.request(request(payload, cookie, seq))
    payload, seq = cipher.encrypt('{"method":"reverse_status"}')
    with pytest.raises(web.HTTPForbidden):
        await receiver.request(request(payload, cookie, seq + 2))
    assert receiver.on_action.call_count == 1


async def test_handshake_two_required_wrong_auth_and_expired_sessions(receiver):
    first = await receiver.handshake1(request(b"a" * 16))
    cookie = first.cookies["TP_SESSIONID"].value
    with pytest.raises(web.HTTPForbidden):
        await receiver.request(request(b"", cookie))
    with pytest.raises(web.HTTPForbidden):
        await receiver.handshake2(request(b"bad-auth", cookie))
    receiver.sessions[cookie].expires = 0
    with pytest.raises(web.HTTPForbidden):
        await receiver.handshake2(request(b"", cookie))
    receiver.on_action.assert_not_called()


@pytest.mark.parametrize("seed", [b"", b"x" * 15, b"x" * 17])
async def test_invalid_seed(receiver, seed):
    with pytest.raises(web.HTTPBadRequest):
        await receiver.handshake1(request(seed))


async def test_session_limit_and_peer_restriction(receiver):
    for _ in range(64):
        await receiver.handshake1(request(b"x" * 16))
    with pytest.raises(web.HTTPServiceUnavailable):
        await receiver.handshake1(request(b"x" * 16))
    handler = AsyncMock()
    with pytest.raises(web.HTTPForbidden):
        await receiver.peer_check(SimpleNamespace(remote="192.0.2.2"), handler)
    handler.assert_not_awaited()


@pytest.mark.parametrize(
    "params", [{"delta": True}, {"delta": -1}, {"delta": 101}, {"delta": "9"}, [], None]
)
def test_invalid_rotation_is_not_emitted(receiver, params):
    assert (
        receiver.dispatch({"method": "increase_brightness", "params": params})[
            "error_code"
        ]
        != 0
    )
    receiver.on_action.assert_not_called()


def test_nested_batch_rejected_before_any_side_effect(receiver):
    reply = receiver.dispatch(
        {
            "method": "multipleRequest",
            "params": {
                "requests": [
                    {"method": "reverse_status"},
                    {"method": "multipleRequest"},
                ]
            },
        }
    )
    assert reply["error_code"] != 0
    receiver.on_action.assert_not_called()


def test_batch_preserves_attribution_and_keepalive_is_quiet(receiver):
    receiver.dispatch(
        {
            "method": "multipleRequest",
            "action_dedup_id": "source",
            "params": {
                "requests": [
                    {"method": "get_device_running_info"},
                    {"method": "reverse_status"},
                ]
            },
        }
    )
    receiver.on_action.assert_called_once()
    assert receiver.on_action.call_args.args[0]["action_dedup_id"] == "source"


def test_discovery_crc_transaction_and_multiple_hub_isolation():
    query = bytes.fromhex("020000010000000000000000463cb5d3")
    result = {"device_id": "F" * 40, "ip": "192.0.2.3:18080"}
    packet = discovery_reply(query, result)
    assert packet[8:12] == query[8:12]
    assert json.loads(packet[16:])["result"] == result
    with pytest.raises(ValueError):
        discovery_reply(query[:-1] + b"\x00", result)
    responder = DiscoveryResponder()
    responder.devices = {"192.0.2.1": result, "192.0.2.2": {"device_id": "E" * 40}}
    responder.connection_made(MagicMock())
    responder.datagram_received(query, ("192.0.2.1", 1000))
    responder.datagram_received(query, ("192.0.2.2", 1001))
    responder.datagram_received(query, ("192.0.2.4", 1002))
    assert responder.transport.sendto.call_count == 2
    assert (
        json.loads(responder.transport.sendto.call_args_list[1].args[0][16:])["result"][
            "device_id"
        ]
        == "E" * 40
    )
