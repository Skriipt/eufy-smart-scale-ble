# Eufy Smart Scale P3 BLE Home Assistant Integration — Design

**Date:** 2026-08-24  
**Repository:** `Skriipt/eufy-smart-scale-ble`  
**Integration domain:** `eufy_p3_ble`  
**Initial version:** `0.1.0`

## 1. Goal

Build a private, local-only Home Assistant custom integration for the Eufy Smart Scale P3 (`eufy T9150`). The integration must read measurements directly from Bluetooth Low Energy advertisements, work through Home Assistant Bluetooth adapters and ESPHome Bluetooth proxies, and reliably publish the completed weight even when a proxy reports multiple manufacturer-data entries containing both stale and current packets.

The first release must expose only values that are transmitted directly by the scale and can be validated from captured packets:

- completed weight;
- real-time weight;
- body impedance;
- heart rate;
- timestamp of the latest completed measurement;
- diagnostic packet status.

## 2. Problem being solved

The upstream `eufylife-ble-client` currently handles the P3/T9150 by selecting the first matching manufacturer-data entry. Some ESPHome Bluetooth proxies provide two entries in one advertisement: an older cached packet, commonly status `0x01`, followed by the current packet, such as status `0x05`. Selecting the first entry leaves `final_weight_kg` unset even though the scale has already locked the measurement.

This integration must not depend on that upstream parser. It will parse the T9150 packets itself and use the packet sequence counter to reject stale or duplicate frames.

## 3. Scope

### Included in version 0.1.0

- T9150/P3 only.
- Automatic Bluetooth discovery and a manual discovery picker.
- Advertisement-only operation; no active GATT connection to the scale.
- Support for local Bluetooth adapters and ESPHome Bluetooth proxies through Home Assistant's Bluetooth integration.
- A dedicated parser and measurement state machine bundled inside the custom integration.
- Restoring completed values after Home Assistant restarts.
- German and English entity/config-flow translations.
- HACS-compatible repository layout plus manual installation instructions.
- Unit tests for packet parsing and state transitions.
- Home Assistant integration tests for discovery, setup, entity updates, restoration, unload, and malformed input.

### Explicitly excluded from version 0.1.0

- Other Eufy scale models.
- Cloud or Eufy account access.
- Writing data back to the Eufy app.
- BMI, body-fat percentage, muscle mass, body water, visceral fat, bone mass, metabolic age, or other derived metrics.
- Reverse-engineering or reproducing Eufy's proprietary profile-based body-composition formulas.
- User/profile recognition.
- Long-term measurement storage outside Home Assistant's Recorder.

## 4. Compatibility and project constraints

- Target Home Assistant: `2026.8.0` and newer.
- Target Python: `3.14.2` and newer, matching Home Assistant 2026.8.
- No external runtime Python package for decoding the P3 protocol.
- No YAML configuration.
- The integration must use a distinct domain, `eufy_p3_ble`, and must not overwrite Home Assistant core files.
- The official `eufylife_ble` integration may technically coexist, but its config entry for the same scale should be removed or ignored to avoid duplicate devices and entities.
- All processing is local. No credentials, tokens, personal profile data, or Internet connection are required.

## 5. Architecture

The integration is split into four focused units:

1. **BLE packet parser** — validates and decodes individual T9150 manufacturer-data frames without Home Assistant dependencies.
2. **Device/session state** — ranks frames by their sequence counter, ignores stale/duplicate data, combines the phases of one weighing session, and notifies subscribers.
3. **Home Assistant setup and discovery** — creates one runtime device per config entry and registers the Bluetooth callback.
4. **Sensor entities** — expose live, restored, and diagnostic values using Home Assistant entity conventions.

The parser remains pure and deterministic. Home Assistant-specific code never interprets raw byte offsets directly.

## 6. Planned repository structure

```text
custom_components/eufy_p3_ble/
├── __init__.py
├── bluetooth.py
├── config_flow.py
├── const.py
├── device.py
├── manifest.json
├── models.py
├── parser.py
├── sensor.py
├── strings.json
└── translations/
    ├── de.json
    └── en.json

tests/
├── conftest.py
├── fixtures/
│   └── t9150_packets.py
├── test_config_flow.py
├── test_device.py
├── test_init.py
├── test_parser.py
└── test_sensor.py

.github/workflows/
└── tests.yml

README.md
hacs.json
pyproject.toml
LICENSE
```

### File responsibilities

- `parser.py`: frame validation, status decoding, byte extraction, sequence comparison helpers.
- `models.py`: immutable frame model, runtime state model, typed config-entry/runtime-data aliases.
- `device.py`: state machine and callback registration; no entity code.
- `bluetooth.py`: selects the newest valid frame from all manufacturer-data entries in a Home Assistant advertisement.
- `__init__.py`: config-entry setup, Bluetooth callback registration, platform forwarding, and unload.
- `config_flow.py`: T9150 discovery, confirmation, manual picker, and unique-ID handling.
- `sensor.py`: entity descriptions and entity implementations.
- `tests/fixtures/t9150_packets.py`: sanitized real packet samples, including the stale-plus-current proxy case.

## 7. T9150 frame model

A valid candidate frame must:

- be at least 19 bytes long;
- originate from a Bluetooth advertisement whose local name is `eufy T9150`;
- contain one of the accepted status values in byte index `10`;
- decode to a plausible weight from bytes `12` and `13`.

Accepted initial statuses:

| Status | Meaning used by the integration | Handling |
|---|---|---|
| `0x01` | live/unstable weight | update real-time weight only |
| `0x05` | weight locked | update completed weight and measurement timestamp |
| `0x15` | post-lock/body-composition phase | retain completed weight; accept newer ancillary data |
| `0x25` | impedance/body-composition phase | retain completed weight; parse impedance when present |
| `0x65` | later body-composition phase | retain completed weight; parse supported ancillary values |
| `0xA5` | later body-composition phase | retain completed weight; parse supported ancillary values |
| `0xE5` | final body-composition phase | retain completed weight; parse impedance and heart rate when present |

Decoded fields:

- **Sequence counter:** byte `6`, unsigned 8-bit.
- **Status:** byte `10`.
- **Weight:** little-endian unsigned integer from bytes `12..13`, divided by `100`, in kilograms.
- **Heart rate:** byte `15` when byte `11` has bit `0x80` set and the value is non-zero.
- **Impedance:** little-endian unsigned integer from bytes `17..18`, divided by `10`, in ohms, when status bit `0x20` is set and the raw value is non-zero.

Plausibility limits used for rejecting corrupt packets:

- weight: greater than `0.0 kg` and at most `200.0 kg`;
- heart rate: `30..240 bpm`;
- impedance: `50..2000 Ω`.

A packet may still update weight/status when an ancillary field is outside its plausibility range; only that ancillary field is discarded.

## 8. Newest-frame selection

Every Bluetooth callback may contain zero, one, or multiple manufacturer-data entries. The selection algorithm is:

1. Parse every entry independently.
2. Drop invalid or unsupported frames.
3. Deduplicate byte-identical frames.
4. Starting from the first valid frame, compare sequence counters using unsigned 8-bit wraparound:

   ```python
   delta = (candidate - reference) & 0xFF
   candidate_is_newer = 0 < delta < 128
   ```

5. Select the newest valid frame.
6. The runtime device compares that sequence against the last accepted sequence and ignores duplicate or older callbacks.

This specifically handles the observed proxy pattern where a stale `0x01` frame appears before a newer `0x05` frame in the same `manufacturer_data` mapping. It also handles a counter transition from `0xFF` to `0x00`.

If two distinct frames have the same sequence counter, the later entry in mapping iteration order wins only when it has a later measurement status according to this rank:

```text
0x01 < 0x05 < 0x15 < 0x25 < 0x65 < 0xA5 < 0xE5
```

## 9. Measurement state machine

The runtime state keeps the last completed measurement separate from the current live frame.

### On status `0x01`

- update `real_time_weight_kg`;
- update diagnostic status and sequence;
- start a new in-memory measurement session when the previous accepted status was not `0x01`;
- clear only session-scoped impedance and heart-rate candidates;
- do not clear the previously completed/restored weight or timestamp.

### On status `0x05`

- update real-time weight;
- set completed weight;
- set `last_measurement_at` to Home Assistant UTC time only on the first final packet of this session;
- retain the timestamp for subsequent body-composition packets belonging to the same session.

### On statuses `0x15`, `0x25`, `0x65`, `0xA5`, or `0xE5`

- retain/update the final weight from the packet;
- update impedance or heart rate only when a valid value is present;
- never replace a valid stored ancillary value with `None` from a later packet;
- keep the original timestamp for the session.

### Session boundary

A new status `0x01` following any final/post-final status starts a new session. Sequence wraparound alone does not start a new session.

## 10. Home Assistant entities

All entities belong to one Bluetooth device named **Eufy Smart Scale P3**, manufacturer **Eufy**, model **T9150**.

| Entity | Type | Persistence | Availability | Notes |
|---|---|---|---|---|
| Weight | weight sensor, kg | restore | always available after first value | only completed measurements |
| Real-time Weight | weight sensor, kg | no restore | Bluetooth address present | latest live frame |
| Impedance | measurement sensor, Ω | restore | always available after first value | raw value broadcast by scale |
| Heart Rate | measurement sensor, bpm | restore | always available after first value | raw value broadcast by scale |
| Last Measurement | timestamp sensor | restore | always available after first value | first lock time of latest session |
| Packet Status | diagnostic sensor | no restore | Bluetooth address present | translated status plus raw hex attribute |

Entity unique IDs use the normalized Bluetooth address plus a stable suffix, for example:

```text
<address>_weight
<address>_real_time_weight
<address>_impedance
<address>_heart_rate
<address>_last_measurement
<address>_packet_status
```

The completed sensors update only when their associated new non-null measurement value arrives. They retain their last value across unrelated packets and Home Assistant restarts.

## 11. Discovery and config flow

The manifest advertises one Bluetooth matcher:

```json
{"local_name": "eufy T9150"}
```

Bluetooth discovery flow:

1. use the scale address as the config-entry unique ID;
2. abort when already configured;
3. confirm the discovered **Eufy Smart Scale P3**;
4. store the model/local name in entry data.

Manual flow:

1. request an active Bluetooth scan;
2. list only currently discovered `eufy T9150` devices not already configured;
3. create the same address-based config entry.

Runtime setup registers an active-mode `BluetoothCallbackMatcher` for the configured address and forwards setup to the sensor platform. Unload unregisters the Bluetooth callback and unloads sensor entities cleanly.

## 12. Error handling and logging

- Invalid length, status, weight, or non-byte manufacturer data is ignored without raising from the Bluetooth callback.
- Expected malformed/unsupported packets log only at debug level.
- A parser exception is contained at the callback boundary and logged once per distinct error signature at warning level, so a bad advertisement cannot break the integration loop or flood logs.
- Duplicate and stale sequence counters are debug-only events.
- The integration does not create a repair issue for transient packet loss; BLE advertisements are naturally lossy.
- Setup must succeed even when the scale is sleeping. Entities populate on the next advertisement.

## 13. Privacy and security

- No network requests.
- No Eufy credentials.
- No profile, age, height, or sex data.
- Bluetooth addresses are stored only in the Home Assistant config entry and entity/device registry as required for device identity.
- Tests and repository fixtures use sanitized packet samples and must not include the user's real Bluetooth address.
- Debug logging must never dump Home Assistant secrets; raw scale packet logging is disabled by default and limited to debug level.

## 14. Testing strategy

### Pure parser tests

- valid live `0x01` frame;
- valid locked `0x05` frame;
- each accepted post-final status;
- impedance extraction;
- heart-rate extraction;
- zero/implausible ancillary values ignored;
- truncated and unsupported frames rejected;
- impossible weight rejected;
- sequence comparison including `0xFF -> 0x00` wraparound.

### Newest-frame regression tests

- one mapping containing stale `0x01` followed by current `0x05` selects `0x05`;
- reversed mapping still selects the higher sequence counter;
- identical duplicated entries are processed once;
- older callback after a newer callback is ignored;
- equal sequence chooses the more advanced status.

### Device/session tests

- live weight does not overwrite completed weight;
- first final packet sets completed weight and timestamp;
- later post-final packets retain that timestamp;
- impedance and heart rate merge into the same completed session;
- a new live packet starts a new session but leaves the previous completed values visible until the next final reading;
- callbacks can be registered and unregistered safely.

### Home Assistant tests

- Bluetooth auto-discovery and confirmation;
- manual discovery picker and no-device abort;
- duplicate config-entry abort;
- config-entry setup while scale is absent;
- creation of all six sensors;
- state updates from mocked Bluetooth advertisements;
- restore behavior for completed entities;
- availability behavior;
- clean unload and callback removal;
- malformed advertisements do not raise.

### Continuous integration

GitHub Actions runs on Python `3.14` and executes:

```text
ruff check
ruff format --check
mypy
pytest --cov=custom_components/eufy_p3_ble
```

Coverage target for parser and device-state modules: at least `95%` branch coverage. Coverage for Home Assistant glue code is measured but not used as a hard gate in version 0.1.0.

## 15. Installation and release model

The repository is private and intended for personal use.

- The root layout remains compatible with adding the repository to HACS as an **Integration** custom repository.
- Manual installation consists of copying `custom_components/eufy_p3_ble` into Home Assistant's `/config/custom_components/` directory and restarting Home Assistant.
- Version `0.1.0` is the first installable test release.
- The README will describe disabling/removing the existing official EufyLife entry for the same T9150 before configuring this integration.

## 16. Acceptance criteria for version 0.1.0

Version 0.1.0 is complete when:

1. Home Assistant discovers the T9150 through an ESPHome Bluetooth proxy.
2. The integration can be configured without YAML or cloud credentials.
3. A weighing session with stale `0x01` and newer `0x05` data updates the **Weight** sensor to the scale's locked value.
4. Real-time weight updates during the session without erasing the previous completed weight.
5. Impedance and heart-rate values appear when the scale broadcasts valid values.
6. The latest completed weight, impedance, heart rate, and timestamp survive a Home Assistant restart.
7. Malformed, duplicate, and out-of-order packets do not cause errors or regress values.
8. All automated tests and static checks pass.
9. Installation instructions are sufficient to install the private integration through HACS or manually.

## 17. Future extensions

Future versions may add additional Eufy models or carefully validated derived metrics, but only as separate approved changes. Derived body-composition values must not be introduced merely by copying an unverified formula from another scale implementation.

## 18. Reference implementation sources

- Home Assistant core integration: `homeassistant/components/eufylife_ble`
- Home Assistant 2026.8 Python baseline: `home-assistant/core` tag `2026.8.0`
- Upstream BLE client: `bdr99/eufylife-ble-client`
- Public P3 investigation and packet samples: upstream issue `bdr99/eufylife-ble-client#3`
