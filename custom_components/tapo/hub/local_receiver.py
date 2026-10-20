"""Authenticated receiver for experimental H100 local push commands."""

import asyncio
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import struct
import time
from typing import Callable, Optional

from aiohttp import web
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def sha256(value):
    return hashlib.sha256(value).digest()


def auth_hash(username, password):
    return sha256(
        hashlib.sha1(username.encode()).digest()
        + hashlib.sha1(password.encode()).digest()
    )


def discovery_reply(query, result):
    """Reply to a TDP probe, preserving its transaction identifier."""
    if len(query) < 16 or query[0] != 2 or query[7] != 0:
        raise ValueError("Invalid discovery header")
    size = int.from_bytes(query[4:6], "big")
    if len(query) != 16 + size:
        raise ValueError("Invalid discovery length")
    check = bytearray(query)
    expected = int.from_bytes(check[12:16], "big")
    check[12:16] = (0x5A6B7C8D).to_bytes(4, "big")
    if binascii.crc32(check) != expected:
        raise ValueError("Invalid discovery CRC")
    payload = json.dumps(
        {"error_code": 0, "result": result}, separators=(",", ":")
    ).encode()
    header = bytearray(query[:16])
    header[4:6] = len(payload).to_bytes(2, "big")
    header[6] = 1
    header[12:16] = (0x5A6B7C8D).to_bytes(4, "big")
    packet = header + payload
    packet[12:16] = binascii.crc32(packet).to_bytes(4, "big")
    return bytes(packet)


class DiscoveryResponder(asyncio.DatagramProtocol):
    """Share one discovery socket between receivers, routing by hub IPv4."""

    def __init__(self):
        self.devices = {}
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, query, address):
        result = self.devices.get(address[0])
        if result is None:
            return
        try:
            reply = discovery_reply(query, result)
        except ValueError:
            return
        self.transport.sendto(reply, address)


@dataclass
class Session:
    client_seed: bytes
    server_seed: bytes
    auth: bytes
    expires: float
    established: bool = False
    last_request: Optional[bytes] = None
    last_reply: Optional[bytes] = None

    def __post_init__(self):
        material = self.client_seed + self.server_seed + self.auth
        self.key = sha256(b"lsk" + material)[:16]
        full_iv = sha256(b"iv" + material)
        self.iv = full_iv[:12]
        self.sequence = int.from_bytes(full_iv[-4:], "big", signed=True)
        self.signing = sha256(b"ldk" + material)[:28]

    def sequence_bytes(self, sequence):
        return struct.pack(">i", sequence)

    def decode(self, body, sequence):
        seq = self.sequence_bytes(sequence)
        if len(body) < 48 or (len(body) - 32) % 16:
            raise ValueError("Invalid encrypted length")
        ciphertext = body[32:]
        expected = sha256(self.signing + seq + ciphertext)
        if not hmac.compare_digest(expected, body[:32]):
            raise ValueError("Invalid authentication")
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv + seq)).decryptor()
        padded = cipher.update(ciphertext) + cipher.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    def encode(self, value, sequence):
        seq = self.sequence_bytes(sequence)
        plain = json.dumps(value, separators=(",", ":")).encode()
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plain) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv + seq)).encryptor()
        ciphertext = cipher.update(padded) + cipher.finalize()
        return sha256(self.signing + seq + ciphertext) + ciphertext


class VirtualReceiver:
    def __init__(
        self, secret, device_id, *, peer=None, on_action: Optional[Callable] = None
    ):
        if (
            len(secret) != 32
            or len(device_id) != 40
            or any(ch not in "0123456789abcdefABCDEF" for ch in device_id)
        ):
            raise ValueError(
                "Require a 32-byte KLAPv2 auth hash and 40-character unique identity"
            )
        self.auth = secret
        self.device_id = device_id
        self.mac = ":".join(
            ["02"] + [device_id[index : index + 2].lower() for index in range(0, 10, 2)]
        )
        self.peer = peer
        self.on_action = on_action or (lambda event: None)
        self.sessions = {}
        self.device_on = False
        self.brightness = 50
        self.action_count = 0

    @web.middleware
    async def peer_check(self, request, handler):
        if self.peer and request.remote != self.peer:
            raise web.HTTPForbidden()
        return await handler(request)

    def application(self):
        app = web.Application(client_max_size=65536, middlewares=[self.peer_check])
        app.router.add_post("/app/handshake1", self.handshake1)
        app.router.add_post("/app/handshake2", self.handshake2)
        app.router.add_post("/app/request", self.request)
        return app

    def current_session(self, request, established=False):
        session = self.sessions.get(request.cookies.get("TP_SESSIONID"))
        if not session or session.expires < time.monotonic():
            raise web.HTTPForbidden()
        if established and not session.established:
            raise web.HTTPForbidden()
        return session

    async def handshake1(self, request):
        seed = await request.read()
        if len(seed) != 16:
            raise web.HTTPBadRequest()
        self.sessions = {
            key: value
            for key, value in self.sessions.items()
            if value.expires >= time.monotonic()
        }
        if len(self.sessions) >= 64:
            raise web.HTTPServiceUnavailable()
        session = Session(
            seed, secrets.token_bytes(16), self.auth, time.monotonic() + 600
        )
        key = secrets.token_hex(16)
        self.sessions[key] = session
        response = web.Response(
            body=session.server_seed
            + sha256(seed + session.server_seed + session.auth),
            content_type="application/octet-stream",
        )
        response.set_cookie("TP_SESSIONID", key, httponly=True, path="/")
        response.set_cookie("TIMEOUT", "600", path="/")
        return response

    async def handshake2(self, request):
        session = self.current_session(request)
        expected = sha256(session.server_seed + session.client_seed + session.auth)
        if not hmac.compare_digest(await request.read(), expected):
            raise web.HTTPForbidden()
        session.established = True
        return web.Response(body=b"")

    async def request(self, request):
        session = self.current_session(request, established=True)
        body = await request.read()
        try:
            sequence = int(request.query["seq"])
            # An identical transport retry must not emit the action twice.
            if (
                session.last_request is not None
                and sequence == session.sequence
                and session.last_request == body
            ):
                return web.Response(
                    body=session.last_reply, content_type="application/octet-stream"
                )
            # H100 masks the sign bit of the derived initial sequence.
            # Accept the authenticated first value; later requests must advance it.
            if session.last_request is not None:
                next_sequence = (
                    0 if session.sequence == 0x7FFFFFFF else session.sequence + 1
                )
                if sequence != next_sequence:
                    raise ValueError("Unexpected sequence")
            value = json.loads(session.decode(body, sequence))
            if not isinstance(value, dict):
                raise ValueError("Require object")
        except (ValueError, KeyError, struct.error, UnicodeError):
            raise web.HTTPForbidden()
        result = self.dispatch(value)
        reply = session.encode(result, sequence)
        session.sequence = sequence
        session.last_request, session.last_reply = body, reply
        return web.Response(body=reply, content_type="application/octet-stream")

    def emit(self, method, params, *, action_dedup_id=None):
        self.action_count += 1
        event = {
            "source": "virtual_tapo_receiver",
            "sequence": self.action_count,
            "received_monotonic": time.monotonic(),
            "method": method,
            "params": params,
            "data_kind": "configured_action_not_raw_knob_event",
        }
        # The firmware copies this top-level field onto LAN action commands.
        # Its rule suffix was verified on H1001.7.10; source mapping is separate.
        if isinstance(action_dedup_id, str) and len(action_dedup_id) <= 128:
            event["action_dedup_id"] = action_dedup_id
        self.on_action(event)

    def dispatch(self, value):
        method = value.get("method")
        action_dedup_id = value.get("action_dedup_id")
        params = value.get("params") or {}
        if not isinstance(params, dict):
            return {"error_code": -1008}
        if method == "multipleRequest":
            items = params.get("requests")
            if not isinstance(items, list) or len(items) > 16:
                return {"error_code": -1008}
            if any(
                not isinstance(item, dict) or item.get("method") == "multipleRequest"
                for item in items
            ):
                return {"error_code": -1008}
            replies = []
            for item in items:
                command = {"action_dedup_id": action_dedup_id, **item}
                replies.append({"method": item.get("method"), **self.dispatch(command)})
            return {"error_code": 0, "result": {"responses": replies}}
        if method == "get_device_info":
            result = {
                "device_id": self.device_id,
                "type": "SMART.TAPOBULB",
                "model": "HA-VIRTUAL",
                "hw_ver": "1.0",
                "fw_ver": "0.0.1",
                "nickname": "SEEgUmVjZWl2ZXI=",
                "device_on": self.device_on,
                "brightness": self.brightness,
                "mac": self.mac.replace(":", "-"),
            }
        elif method == "component_nego":
            result = {
                "component_list": [
                    {"id": name, "ver_code": version}
                    for name, version in [
                        ("device", 2),
                        ("brightness", 1),
                        ("localSmart", 1),
                        ("bulb_quick_control", 1),
                    ]
                ]
            }
        elif method == "get_device_running_info":
            result = {
                "device_on": self.device_on,
                "brightness": self.brightness,
                "on_time": 0,
                "overheated": False,
            }
        elif method == "reverse_status":
            self.device_on = not self.device_on
            self.emit(method, {}, action_dedup_id=action_dedup_id)
            result = {}
        elif method in ("increase_brightness", "decrease_brightness"):
            delta = params.get("delta")
            if type(delta) is not int or not 0 <= delta <= 100:
                return {"error_code": -1008}
            direction = 1 if method == "increase_brightness" else -1
            self.brightness = max(1, min(100, self.brightness + direction * delta))
            self.emit(method, {"delta": delta}, action_dedup_id=action_dedup_id)
            result = {}
        elif method == "set_device_info":
            accepted = {}
            if "device_on" in params:
                if type(params["device_on"]) is not bool:
                    return {"error_code": -1008}
                accepted["device_on"] = params["device_on"]
            if "brightness" in params:
                if (
                    type(params["brightness"]) is not int
                    or not 1 <= params["brightness"] <= 100
                ):
                    return {"error_code": -1008}
                accepted["brightness"] = params["brightness"]
            if not accepted:
                return {"error_code": -1008}
            for key, item in accepted.items():
                setattr(self, key, item)
            self.emit(method, accepted, action_dedup_id=action_dedup_id)
            result = {}
        else:
            return {"error_code": -1002}
        return {"error_code": 0, "result": result}
