# H100 / S200D local push

H100-connected S200D knobs now send events to Home Assistant through the hub's native Local Smart Actions transport. The integration runs an authenticated virtual receiver and manages four local hub rules per enabled knob: single click, double click, clockwise rotation, and counterclockwise rotation. No root access, firmware flashing, MQTT broker, physical receiver bulb, or manually created Tapo automation is needed.

This replaces high-frequency event-log polling for **H100 / S200D**. Battery and ordinary device information still refresh at the configured interval. Other hub/device combinations keep their existing handling; this does not claim H110, H200, H500, or S200B push support.

The protocol is undocumented. Hardware verification covers H100 firmware **1.7.10 Build260725 Rel042335**, two S200D knobs, and Home Assistant 2026.5.3. Other H100 firmware versions need verification. Treat this as an experimental transport with an explicit compatibility boundary, rather than a supported TP-Link API.

## First setup

1. Pair the S200D to the H100 in the Tapo app. Confirm the hub and knob are online.
2. Install the integration, restart Home Assistant, and add the H100 using its IPv4 address and Tapo account credentials.
3. The **Set up S200D local events** screen lists the paired S200D knobs, selected by default. Review the network settings below, leave **Legacy rotation degrees (compatibility)** off for native events, then submit. An empty selection disables knob events; it does not fall back to polling.
4. Wait for the hub's **Local Push** diagnostic sensor to show `connected`.
5. Press and rotate each knob. The existing button and dial event entities should update. Add a Home Assistant automation using those entities or the `tapo_local_push` event below.

The integration configures transport and source attribution. The actions your knobs perform remain configurable through Home Assistant automations; installing the integration does not change lights automatically.

## Existing installations and later changes

Existing H100/S200D installations without saved push settings automatically use local push for their associated knobs after upgrading. Existing event entity unique IDs and the `rotation` event type remain unchanged. Native direction and amount are the default, including entries without a saved compatibility setting. If an existing automation reads signed `degrees`, enable **Legacy rotation degrees (compatibility)** during setup or in Configure. This adds the compatibility field for all selected knobs on that hub without changing the native fields or enabling polling. Confirm receiver connectivity after upgrading. Other firmware and deltas outside the mapping below need verification.

Open **Settings → Devices & services → TP-Link Tapo → H100 → Configure** to change:

| Setting | Default | Purpose |
| --- | --- | --- |
| S200D knobs using local push | All associated S200D knobs when no selection has been saved | Choose which knobs emit events. Deselecting disables their event entities. |
| Receiver TCP port | `18080` | Choose an unused unprivileged port between `1024` and `65535`. |
| Receiver IPv4 address | Automatic | Use the local address on Home Assistant's route to the hub, or specify a local IPv4 address for multi-adapter hosts. |
| Legacy rotation degrees (compatibility) | Off | Add reconstructed signed `degrees` for existing automations on all selected knobs. Native direction and amount are always retained. |
| Device information refresh interval | Existing setting, normally 30 seconds | Battery and ordinary device information, independent of push events. |

Saving options reloads the integration and reconciles its rules. Pair new knobs in the Tapo app first, then select them in Configure. Setup validates device selection, IPv4 addresses, and local socket availability before saving; it does not test firewall reachability. If a receiver cannot bind during startup, the setup error directs you to Configure so you can fix the address/port.

The previous Poll Latency and Poll Utilization entities are no longer created for H100/S200D. Their old registry entries may remain unavailable after upgrade and can be removed in Home Assistant. There is no background fast-polling fallback for these knobs.

## Network requirements

Use a stable IPv4 address for both the hub and Home Assistant. The receiver address must be assigned to the machine/network namespace running Home Assistant, and must be reachable from the hub.

| Direction | Destination | Purpose |
| --- | --- | --- |
| H100 → Home Assistant | TCP receiver port, default `18080` | Authenticated KLAPv2 commands and keepalive |
| H100 → Home Assistant | UDP `20002` | Discovery queries and replies |
| Home Assistant → H100 | UDP `21112` | Receiver discovery announcements and withdrawal |
| Home Assistant → H100 | Existing hub API connection | Registration checks and managed rule reconciliation |

Stateful firewall rules must allow the corresponding replies. Guest Wi-Fi isolation or VLAN rules can prevent communication even when local socket validation succeeds. No router internet port forwarding is needed; keep these ports local.

**Port 80 and an NGINX proxy are not required.** The verified H100 firmware honors an embedded `IPv4:port` discovery address. The receiver uses that behavior to advertise your configured TCP port. It is firmware-specific behavior, covered by protocol fixtures and hardware testing rather than a TP-Link guarantee.

Home Assistant OS uses the host network. For Home Assistant Container, host networking is recommended. A bridge-networked container's automatic address may be unreachable from the hub; the override cannot bind an address absent from the container. Merely publishing the HTTP port does not solve discovery/address advertisement.

Multiple H100 entries can share discovery UDP `20002` on one local IPv4 address. Each receiver on that address needs a different TCP port. Queries are routed by the configured hub's source IPv4 address. Another application already owning discovery UDP `20002` remains a conflict that must be resolved.

## Events and migration

Existing button event entities emit `single_click` or `double_click`. Dial entities emit `rotation`. Push events include `transport: local_push` and the native Tapo `device_id`; rotation attributes use native `direction`, `amount`, and `signed_amount` by default. Enabling **Legacy rotation degrees (compatibility)** additionally includes signed `degrees` using the lookup below, without any event-log reads.

The same events are also published on Home Assistant's event bus:

```yaml
event_type: tapo_local_push
data:
  device_id: KNOB_TAPO_DEVICE_ID
  transport: local_push
  event_type: rotation
  direction: clockwise
  amount: 9
  signed_amount: 9
  action_id: LC6...
```

- `amount` is the positive native brightness delta, from 1 through 100. It is a percentage-style change, not an angle or a count of physical detents.
- `signed_amount` is positive clockwise and negative counterclockwise.
- With **Legacy rotation degrees (compatibility)** enabled, `degrees` preserves the signed integer used by existing rotation automations for recognized S200D 30-degree steps: positive clockwise, negative counterclockwise. Unknown deltas explicitly set `degrees: null`, while native direction and amount remain available. Do not treat `null` as a measured zero or round an unknown delta to the nearest step. With compatibility disabled, the `degrees` field is absent.
- `action_id` is the hub's opaque deduplication identifier. Source attribution is derived from the verified rule suffix encoded in that identifier. Unknown or ambiguous sources are rejected instead of guessing a knob.
- The receiver suppresses exact encrypted retries and the manager suppresses repeated action identifiers within its bounded in-memory window. It does not promise durable exactly-once delivery across Home Assistant restarts.
- No retained button/dial events are replayed as new actions during Home Assistant startup.

### Degree compatibility and verification

**Legacy rotation degrees (compatibility)** is off by default. Leave it off for new automations, which can consume the actual native delta using `signed_amount`. Enable it only for existing degree-based automations; for example, the event above also includes `degrees: 30` when compatibility is enabled. Turning compatibility off removes that field on subsequent rotations and retains the native values.

The hub sends a brightness delta rather than a raw angle. Firmware analysis found `delta = ceil(abs(degrees) * 100 / 360)`. This rounding cannot be inverted for arbitrary angles: 29, 30, 31, and 32 degrees all produce delta 9. It is invertible for the 30-degree increments observed from S200D knobs:

| Native delta | Degree magnitude | Native delta | Degree magnitude |
| --- | --- | --- | --- |
| 9 | 30 | 59 | 210 |
| 17 | 60 | 67 | 240 |
| 25 | 90 | 75 | 270 |
| 34 | 120 | 84 | 300 |
| 42 | 150 | 92 | 330 |
| 50 | 180 | 100 | 360 |

Direction supplies the sign. The lookup restores legacy `degrees` for these increments; it does not multiply every delta by 3.6 or claim to recover arbitrary angles. In compatibility mode, any other valid delta (for example, 7) still includes direction and native amount, with `degrees: null`. The dial entity explicitly clears any previous degree value for that event. New automations can use `signed_amount` without depending on this angle reconstruction.

On H100 **1.7.10 Build260725 Rel042335** with two S200D knobs running **1.12.0 Build231121 Rel092508**, 672 uniquely matched pushed rotations recovered the original logged signed degrees with zero mismatches. This includes a controlled 36-rotation test (18 per knob) with rapid turns and direction reversals, with no missing or duplicate recorded events. Correlation used the knob identity, the trigger-event suffix in the native action identifier, and timestamps. The controlled comparison used Home Assistant's recorded event entities and the hub's original logs. Historical records without a unique counterpart were excluded.

Observed raw magnitudes covered 30 through 210 degrees. Lookup entries above 210 follow the firmware formula but have not been observed on hardware. Other firmware, non-30-degree reports, and angles above 360 remain unverified. Firmware that sends arbitrary angles could produce a recognized delta with a different original angle; this compatibility mapping is not proof of universal raw-angle fidelity. Sanitized observed delta/angle pairs are included in `tests/fixtures/h100_rotation_degrees.json`.

Use **Developer tools → Events → Listen to events** with `tapo_local_push`, then operate a knob to obtain its native `device_id`. Filter automations by that ID so multiple knobs remain independent. The ID is also included in event entity attributes after a pushed event.

Example for a single light (replace the device and entity IDs):

```yaml
alias: S200D light control
triggers:
  - trigger: event
    event_type: tapo_local_push
    event_data:
      device_id: KNOB_TAPO_DEVICE_ID
actions:
  - choose:
      - conditions: "{{ trigger.event.data.event_type == 'single_click' }}"
        sequence:
          - action: light.toggle
            target:
              entity_id: light.your_light
      - conditions: "{{ trigger.event.data.event_type == 'rotation' }}"
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.your_light
            data:
              brightness_step_pct: "{{ trigger.event.data.signed_amount | int(0) }}"
              transition: 0.15
mode: queued
max: 100
```

### Dimming several lights together

Avoid calculating successive relative steps from a light group's reported brightness when members can report at different times or remain stale. The group's average can lag behind the latest command, causing a later brighten step to send a lower target to an already brighter bulb.

Keep the **requested** brightness in an `input_number` helper (range 1–255), update that helper from each signed delta, and send an absolute `brightness` value to the group members. Calculate the next target from the helper, not from group feedback. Queue the controller so each event sees the preceding requested value. If you also remember on/off intent, keep it separately from stale bulb on/off reports. Explicit dashboard/voice brightness changes should synchronize the target helper without feeding the knob's own commands back into its tracker.

The transport does not prescribe dimming sensitivity, restore behavior, or light group membership; these remain automation choices.

## Diagnostics, cleanup, and recovery

The hub's **Local Push** sensor reports `starting`, `connecting`, `connected`, `error`, or `stopped`, together with receiver address/port, selected device IDs, owned rule IDs, command count, last receipt time, and last error type. Counters are per manager lifetime and reset on reload. `connected` means registration and the managed rules were verified; it is not an end-to-end firewall test. Check a physical gesture as part of setup.

The integration persists a random receiver identity and its owned rule IDs in a private Home Assistant Store. Ownership is saved before any hub writes. New rules are created disabled, read back and verified, then enabled and verified again. Rule contents and source suffixes must remain unambiguous. An incomplete native rule snapshot or ownership conflict causes an error rather than overwriting/deleting unknown rules.

On unload, the integration removes only its verified owned rules, withdraws its own receiver, and closes its sockets and private HTTP session. The original Tapo rules are preserved. Cleanup is bounded when the hub is offline; ownership is retained for recovery on a later push-enabled setup. If disabling while the hub is unreachable leaves rules on it, reconnect the hub and enable push once more, then disable it while connected so cleanup can finish. Do not delete the private Store while hub rules still refer to the receiver.

Registration and rules are reconciled periodically. Automated tests cover idempotent reconciliation, resource cleanup, source isolation, and retry handling. Hardware tests verified custom-port operation, two independent knobs, local operation during a temporary hub internet block, and recovery after a Tapo integration reload with stable receiver/rule identities. Hub power-cycle recovery, long-duration operation, other hub models, and other firmware versions remain unverified.

Receiver authentication uses the existing Tapo account credentials; it does not accept blank/default credentials. Incoming HTTP and discovery requests are restricted to the configured H100 source address. No credentials or derived authentication hash are included in diagnostics.
