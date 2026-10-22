"""H100 local action receiver and owned-rule lifecycle.

This uses undocumented H100 1.7.10 behavior. Rotation retains the native
brightness delta; optional legacy degrees use S200D's observed 30-degree steps.
"""

import asyncio
from collections import OrderedDict
import hashlib
import ipaddress
import logging
import secrets
import socket
import time

import aiohttp
from aiohttp import web
from homeassistant.components.network import async_get_source_ip
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, callback
from homeassistant.helpers.storage import Store
from plugp100.api.requests.tapo_request import TapoRequest
from plugp100.common.credentials import AuthCredential
from plugp100.devices.factory import DeviceConnectConfiguration, connect

from .local_receiver import (
    DiscoveryResponder,
    VirtualReceiver,
    auth_hash,
    discovery_reply,
)

_LOGGER = logging.getLogger(__name__)
CONF_LOCAL_PUSH_DEVICES = "local_push_device_ids"
CONF_LOCAL_PUSH_PORT = "local_push_port"
CONF_LOCAL_PUSH_HOST = "local_push_host"
CONF_LOCAL_PUSH_LEGACY_DEGREES = "local_push_legacy_degrees"
DEFAULT_LOCAL_PUSH_PORT = 18080
EVENT_LOCAL_PUSH = "tapo_local_push"
DISCOVERY_KEY = "tapo_local_push_discovery"
DISCOVERY_LOCK_KEY = "tapo_local_push_discovery_lock"
GESTURES = {
    "single_click": ("singleClick", "reverseStatus", "reverse_status"),
    "double_click": ("doubleClick", "reverseStatus", "reverse_status"),
    "positive": ("rotation", "increaseBrightness", "increase_brightness"),
    "negative": ("rotation", "decreaseBrightness", "decrease_brightness"),
}
# H100 derives delta as ceil(abs(degrees) * 100 / 360). Its rounded output
# is invertible on S200D's observed 30-degree steps, not on arbitrary angles.
# Verified against 672 paired rotations on H100 1.7.10 / S200D 1.12.0;
# see docs/local-push.md. Never snap an unknown delta to a guessed angle.
_S200D_DEGREES_BY_DELTA = {
    9: 30,
    17: 60,
    25: 90,
    34: 120,
    42: 150,
    50: 180,
    59: 210,
    67: 240,
    75: 270,
    84: 300,
    92: 330,
    100: 360,
}


async def async_validate_push(hass, data, choices, current=None):
    """Check settings before saving, without registering or modifying hub rules."""
    selected = set(data.get(CONF_LOCAL_PUSH_DEVICES, []))
    if not selected:
        return {}
    if not selected <= {choice["value"] for choice in choices}:
        return {CONF_LOCAL_PUSH_DEVICES: "invalid_push_devices"}
    try:
        host = data.get(CONF_LOCAL_PUSH_HOST) or await async_get_source_ip(
            hass, target_ip=data["host"]
        )
        address = ipaddress.IPv4Address(host)
        ipaddress.IPv4Address(data["host"])
        if address.is_unspecified or address.is_multicast:
            raise ValueError("Unicast receiver address required")
    except (ValueError, OSError):
        return {CONF_LOCAL_PUSH_HOST: "invalid_receiver_address"}
    port = data.get(CONF_LOCAL_PUSH_PORT, DEFAULT_LOCAL_PUSH_PORT)
    try:
        if (
            not current
            or not current.listening
            or (current.host, current.port) != (str(address), port)
        ):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind((str(address), port))
        if str(address) not in hass.data.get(DISCOVERY_KEY, {}):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.bind((str(address), 20002))
    except OSError:
        return {"base": "receiver_unavailable"}
    return {}


class LocalPushManager:
    """Receive actions, attribute owned rules, and recover registration."""

    def __init__(self, hass, entry, hub, device_ids, host, port):
        self.hass, self.entry, self.hub = hass, entry, hub
        self.legacy_degrees = entry.data.get(CONF_LOCAL_PUSH_LEGACY_DEGREES, False)
        self.device_ids = set(device_ids)
        self.host, self.port = str(ipaddress.IPv4Address(host)), int(port)
        self.hub_host = str(ipaddress.IPv4Address(entry.data["host"]))
        if hub.model != "H100" or not 1024 <= self.port <= 65535:
            raise ValueError("Local push requires H100 and an unprivileged TCP port")
        self._store = Store(
            hass,
            1,
            f"tapo.local_push.{entry.entry_id}",
            private=True,
            atomic_writes=True,
        )
        self._state = {}
        self._listeners = {}
        self._status_listeners = set()
        self._seen = OrderedDict()
        self._routes = {}
        self._runner = self._transport = self._session = self._client = None
        self._responder = None
        self._task = self._stop_unsub = None
        self._stop = asyncio.Event()
        self.available = False
        self.status = "starting"
        self.last_error = None
        self.received_commands = 0
        self.last_received = None
        self._last_reconciled = 0.0

    @property
    def receiver_id(self):
        return self._state.get("receiver_id")

    @property
    def rule_ids(self):
        return sorted(rule["id"] for rule in self._state.get("rules", []))

    @property
    def listening(self):
        """Whether this manager actually owns its receiver sockets."""
        return (
            not self._stop.is_set()
            and self._runner is not None
            and self._transport is not None
        )

    @callback
    def subscribe(self, device_id, listener):
        listeners = self._listeners.setdefault(device_id, set())
        listeners.add(listener)
        return lambda: listeners.discard(listener)

    @callback
    def subscribe_status(self, listener):
        self._status_listeners.add(listener)
        return lambda: self._status_listeners.discard(listener)

    @callback
    def _set_status(self, status, error=None):
        self.status, self.last_error = status, error
        self.available = status == "connected"
        for listener in tuple(self._status_listeners):
            try:
                listener()
            except Exception:
                _LOGGER.exception("Local push status listener failed")

    async def async_start(self):
        """Prepare the receiver; bind and reconcile in a retrying background task."""
        self._state = await self._store.async_load() or {}
        self._state.setdefault("receiver_id", secrets.token_hex(20).upper())
        self._state.setdefault("rules", [])
        await self._store.async_save(self._state)
        data = self.entry.data
        owner = hashlib.md5(data["username"].encode()).hexdigest()
        self._receiver = VirtualReceiver(
            auth_hash(data["username"], data["password"]),
            self.receiver_id,
            peer=self.hub_host,
            on_action=self._on_action,
        )
        self._discovery = {
            "device_type": "SMART.TAPOBULB",
            "device_model": "HA-VIRTUAL",
            "device_id": self.receiver_id,
            # This H100 parser honors the first embedded port despite appending :80.
            "ip": f"{self.host}:{self.port}",
            "mac": self._receiver.mac,
            "owner": owner,
            "factory_default": False,
            "mgt_encrypt_schm": {
                "encrypt_type": "KLAP",
                "lv": 2,
                "http_port": self.port,
                "is_support_https": False,
            },
        }
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=12),
            cookie_jar=aiohttp.CookieJar(unsafe=True),
        )
        self._stop_unsub = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._on_stop
        )
        self._task = self.hass.async_create_background_task(
            self._run(), "Tapo H100 local push"
        )

    async def _async_bind(self):
        """Publish socket ownership only after both receiver endpoints are ready."""
        runner = web.AppRunner(self._receiver.application(), access_log=None)
        try:
            await runner.setup()
            await web.TCPSite(runner, self.host, self.port).start()
            lock = self.hass.data.setdefault(DISCOVERY_LOCK_KEY, asyncio.Lock())
            async with lock:
                endpoints = self.hass.data.setdefault(DISCOVERY_KEY, {})
                responder = endpoints.get(self.host)
                if responder is None:
                    _, responder = await self.hass.loop.create_datagram_endpoint(
                        DiscoveryResponder, local_addr=(self.host, 20002)
                    )
                    endpoints[self.host] = responder
                if self.hub_host in responder.devices:
                    raise ValueError("This hub already has a local push receiver")
                responder.devices[self.hub_host] = self._discovery
                self._responder = responder
                self._transport = responder.transport
        except BaseException:
            await runner.cleanup()
            raise
        self._runner = runner

    async def _connect(self):
        cfg = DeviceConnectConfiguration(
            host=self.hub_host,
            credentials=AuthCredential(
                self.entry.data["username"], self.entry.data["password"]
            ),
            device_type="SMART.TAPOHUB",
            encryption_type="klap",
            encryption_version=2,
        )
        self._client = (await asyncio.wait_for(connect(cfg, self._session), 15)).client

    async def _query(self, obj, method, params):
        if self._client is None:
            await self._connect()
        result = await asyncio.wait_for(
            self._client.execute_raw_request(
                TapoRequest(
                    "debug_nbus", {"obj": obj, "method": method, "params": params}
                )
            ),
            15,
        )
        return result.get_or_raise()

    def _announce(self, withdrawing=False):
        value = dict(self._discovery)
        if withdrawing:
            value.update(owner="0" * 32, factory_default=True)
        packet = discovery_reply(
            bytes.fromhex("020000010000000000000000463cb5d3"), value
        )
        self._transport.sendto(packet, (self.hub_host, 21112))

    async def _registered(self):
        response = await self._query("action_manager", "get_local_device_list", {})
        return any(
            (item.get("device_id") if isinstance(item, dict) else item)
            == self.receiver_id
            for item in response.get("device_list", [])
        )

    async def _run(self):
        while not self._stop.is_set():
            try:
                if not self.listening:
                    await self._async_bind()
                self._announce()
                if not await self._registered():
                    self._routes = {}
                    self._set_status("connecting")
                    self._last_reconciled = 0
                elif time.monotonic() - self._last_reconciled >= 30:
                    await self._reconcile()
                    self._last_reconciled = time.monotonic()
                    self._set_status("connected")
                elif not self.available:
                    self._set_status("connected")
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self._routes = {}
                self._client = None
                self._last_reconciled = 0
                self._set_status("error", type(error).__name__)
                _LOGGER.warning(
                    "H100 local push reconciliation failed: %s", type(error).__name__
                )
            try:
                await asyncio.wait_for(
                    self._stop.wait(), 5 if not self.available else 15
                )
            except TimeoutError:
                pass

    def _rule_input(self, rule, enabled, version):
        event, service, _ = GESTURES[rule["gesture"]]
        trigger = {"thingName": rule["device_id"], "event": {"name": event}}
        if event == "rotation":
            trigger["event"]["paramList"] = [
                {
                    "key": "rotate_deg",
                    "dataType": "INT",
                    "op": "GT" if rule["gesture"] == "positive" else "LT",
                    "value": {"data": "0"},
                }
            ]
        return {
            "smartPk": {"id": rule["id"]},
            "version": version,
            "enabled": enabled,
            "effectivePeriod": {"periodType": "ALL_DAY", "daysOfWeek": 127},
            "triggerSetting": {"condition": 0, "things": [trigger]},
            "actionSetting": {
                "things": [
                    {
                        "thingName": self.receiver_id,
                        "service": {"serviceId": service, "inputParams": {}},
                    }
                ]
            },
        }

    def _owns_native_rule(self, rule, native):
        """Refuse mutation unless the persisted rule still has our source/target."""
        actions = native.get("action_setting_list", [])
        teams = native.get("trigger_team_list", [])
        events = [event for team in teams for event in team.get("event_list", [])]
        expected_event, expected_service, _ = GESTURES[rule["gesture"]]
        predicates = []
        if rule["gesture"] in ("positive", "negative"):
            op = "GT" if rule["gesture"] == "positive" else "LT"
            predicates = [f'"rotate_deg":  __{op}[0]']
        return (
            native.get("id") == rule["id"]
            and len(actions) == 1
            and len(events) == 1
            and len(teams) == 1
            and teams[0].get("team") == 0
            and teams[0].get("team_type") == 0
            and native.get("condition") == 0
            and native.get("condition_type") == 0
            and native.get("effective_periods")
            == [
                {
                    "period_type": 0,
                    "days_of_week": 127,
                    "start_time": 0,
                    "end_time": 0,
                    "start_type": 0,
                    "end_type": 0,
                }
            ]
            and actions[0].get("device_id") == self.receiver_id
            and actions[0].get("type") == 3
            and actions[0].get("delay_seconds") == 0
            and actions[0].get("future_type") == 0
            and not actions[0].get("action_id")
            and actions[0].get("service", {}).get("id") == expected_service
            and actions[0].get("service", {}).get("params") == {}
            and events[0].get("device_id") == rule["device_id"]
            and events[0].get("event_id") == expected_event
            and events[0].get("param_list") == predicates
        )

    async def _native_rules(self):
        response = await self._query(
            "action_manager", "debug", {"method": "rule_content", "index": 0}
        )
        rules = response.get("rule_content_list", [])
        native = {rule["id"]: rule for rule in rules}
        if response.get("sum", len(rules)) != len(native):
            raise RuntimeError("Incomplete native rule snapshot; refusing mutation")
        return native

    async def _delete_owned(self, rules, native):
        found = [rule for rule in rules if rule["id"] in native]
        if any(not self._owns_native_rule(rule, native[rule["id"]]) for rule in found):
            raise RuntimeError("Owned rule content changed; refusing deletion")
        if found:
            await self._query(
                "action_manager",
                "delete_rule",
                {"delete_list": [{"id": r["id"]} for r in found]},
            )

    async def _reconcile(self):
        """Publish a complete verified route map or invalidate every old route."""
        try:
            await self._async_reconcile_rules()
        except BaseException:
            self._routes = {}
            raise

    async def _async_reconcile_rules(self):
        native = await self._native_rules()
        identifiers = set(native) | {rule["id"] for rule in self._state["rules"]}
        for rule in self._state["rules"]:
            if any(
                identifier != rule["id"] and identifier[-5:] == rule["id"][-5:]
                for identifier in identifiers
            ):
                raise RuntimeError("Ambiguous source rule suffix; refusing mutation")
        retired = [
            r for r in self._state["rules"] if r["device_id"] not in self.device_ids
        ]
        await self._delete_owned(retired, native)
        self._state["rules"] = [r for r in self._state["rules"] if r not in retired]
        tokens = {r["id"][-5:] for r in self._state["rules"]}
        tokens.update(identifier[-5:] for identifier in native)
        for device_id in sorted(self.device_ids):
            for gesture in GESTURES:
                if any(
                    r["device_id"] == device_id and r["gesture"] == gesture
                    for r in self._state["rules"]
                ):
                    continue
                identifier = "H" + secrets.token_hex(4)[:7]
                while identifier[-5:] in tokens:
                    identifier = "H" + secrets.token_hex(4)[:7]
                tokens.add(identifier[-5:])
                self._state["rules"].append(
                    {"id": identifier, "device_id": device_id, "gesture": gesture}
                )
        # Persist ownership BEFORE any hub write, so an interrupted setup can recover.
        await self._store.async_save(self._state)
        routes = {}
        for rule in self._state["rules"]:
            current = native.get(rule["id"])
            if current and not self._owns_native_rule(rule, current):
                raise RuntimeError("Rule ID conflict; refusing replacement")
            if current is None:
                await self._query(
                    "action_manager", "update_rule", self._rule_input(rule, False, 1)
                )
                current = (await self._native_rules()).get(rule["id"])
                if (
                    not current
                    or not self._owns_native_rule(rule, current)
                    or current.get("enabled")
                ):
                    raise RuntimeError("Disabled rule ownership was not verified")
            if not current.get("enabled"):
                await self._query(
                    "action_manager",
                    "update_rule",
                    self._rule_input(rule, True, current["version"] + 1),
                )
                current = (await self._native_rules()).get(rule["id"])
                if (
                    not current
                    or not self._owns_native_rule(rule, current)
                    or not current.get("enabled")
                ):
                    raise RuntimeError("Active rule ownership was not verified")
            token = rule["id"][-5:]
            if token in routes:
                raise RuntimeError("Ambiguous source rule suffix")
            routes[token] = rule
        self._routes = routes

    @callback
    def _on_action(self, action):
        if not self.available:
            return
        dedup = action.get("action_dedup_id")
        if (
            not isinstance(dedup, str)
            or len(dedup) != 25
            or not dedup.startswith("LC6")
        ):
            return
        rule = self._routes.get(dedup[8:13])
        if not rule or rule["device_id"] not in self.device_ids:
            return
        now = time.monotonic()
        while self._seen and next(iter(self._seen.values())) < now - 600:
            self._seen.popitem(last=False)
        if action["method"] != GESTURES[rule["gesture"]][2] or dedup in self._seen:
            return
        self._seen[dedup] = now
        while self._seen and (
            len(self._seen) > 1024 or next(iter(self._seen.values())) < now - 600
        ):
            self._seen.popitem(last=False)
        if self.hass.state is not CoreState.running:
            return
        event = {
            "device_id": rule["device_id"],
            "transport": "local_push",
            "event_type": rule["gesture"],
            "action_id": dedup,
        }
        if rule["gesture"] in ("positive", "negative"):
            amount = action["params"].get("delta")
            if type(amount) is not int or not 1 <= amount <= 100:
                return
            sign = 1 if rule["gesture"] == "positive" else -1
            event.update(
                event_type="rotation",
                direction="clockwise" if sign > 0 else "counterclockwise",
                amount=amount,
                signed_amount=sign * amount,
            )
            if self.legacy_degrees:
                degrees = _S200D_DEGREES_BY_DELTA.get(amount)
                event["degrees"] = sign * degrees if degrees is not None else None
        self.received_commands += 1
        self.last_received = time.time()
        self._set_status(self.status, self.last_error)
        self.hass.bus.async_fire(EVENT_LOCAL_PUSH, event)
        for listener in tuple(self._listeners.get(rule["device_id"], ())):
            try:
                listener(event)
            except Exception:
                _LOGGER.exception("Local push entity listener failed")

    async def _on_stop(self, event):
        await self.async_stop()

    async def async_stop(self):
        """Remove only verified owned rules, withdraw, and close sockets."""
        if self._stop.is_set():
            return
        self._stop.set()
        self._routes = {}
        if self._stop_unsub:
            self._stop_unsub()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        try:
            if self._state.get("rules") and self._session and not self._session.closed:
                async with asyncio.timeout(10):
                    await self._delete_owned(
                        self._state.get("rules", []), await self._native_rules()
                    )
        except Exception as error:
            _LOGGER.warning(
                "Could not remove owned push rules; ownership retained for recovery: %s",
                type(error).__name__,
            )
        if self._transport:
            try:
                self._announce(withdrawing=True)
                await asyncio.sleep(0.1)
            except OSError:
                _LOGGER.debug("Could not send receiver withdrawal")
            async with self.hass.data[DISCOVERY_LOCK_KEY]:
                self._responder.devices.pop(self.hub_host, None)
                if not self._responder.devices:
                    self._transport.close()
                    self.hass.data[DISCOVERY_KEY].pop(self.host, None)
        try:
            if self._runner:
                await self._runner.cleanup()
        finally:
            if self._session:
                await self._session.close()
            self._set_status("stopped")
