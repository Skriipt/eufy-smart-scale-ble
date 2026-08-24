# Eufy Multi-Scale Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the current P3-only Home Assistant integration into a privacy-safe, capability-driven Eufy Smart Scale BLE integration supporting every model currently handled by Home Assistant's `eufylife_ble` integration, while clearly distinguishing hardware-verified, upstream-validated, experimental, and unsupported capabilities.

**Architecture:** Split model identity, transport, protocol parsing, session handling, entity exposure, and body-composition calculation into independent layers. Every model declares per-capability support; Home Assistant entities are only created when the selected model can actually provide the required raw data. Passive advertisement models stay passive wherever possible; GATT is used only for models or optional capabilities that require an active connection.

**Tech Stack:** Python 3.14, Home Assistant 2026.8+, Home Assistant Bluetooth stack, Bleak/`bleak-retry-connector` through Home Assistant, pytest, pytest-homeassistant-custom-component, Ruff, mypy, HACS validation, Hassfest.

**Spec:** This document, especially the sections “Approved design decisions”, “Support-level semantics”, and “Model protocol matrix”.

## Global Constraints

- The public repository must never contain real user measurements, MAC addresses, body-profile data, or copied raw captures from real people.
- All committed packet fixtures must be synthetic and generated from documented protocol layouts.
- Standard Home Assistant diagnostics must never contain raw BLE frames, addresses, weight, impedance, heart rate, sex, height, age, or other personal measurement/profile values.
- `Verified` means tested with real hardware by the project maintainer.
- `Upstream Validated` means the protocol/behavior is implemented and supported by reputable upstream projects but has not been tested by this project with real hardware.
- `Experimental` means there is plausible protocol evidence, but the field/behavior is not sufficiently validated to expose as a normal supported capability.
- Experimental raw fields must be disabled by default unless explicitly stated otherwise.
- Body-composition entities must only be created when a reliable same-session weight and impedance pair is available. Do not invent or substitute BMI-only body-fat estimates for models whose impedance cannot be decoded.
- The existing P3 behavior must not regress while the architecture is generalized.
- Do not copy GPL source code into this MIT repository. GPL projects may be used only as behavioral/protocol cross-checks; implementation must be independently written from protocol facts and MIT/compatible references.
- Home Assistant, HACS, Hassfest, Ruff, mypy, compile checks, and the full pytest suite must be green before each merge.
- Each protocol-family PR must contain its own synthetic tests, documentation update, and support-matrix update.
- The official HACS-store submission remains out of scope until this multi-model work is stable.

---

# Approved design decisions

## 1. Integration scope

Target every model currently advertised by Home Assistant's `eufylife_ble` integration:

- T9120 — Smart Scale A1
- T9130 — Smart Scale C20
- T9140 — Smart Scale
- T9146 — Smart Scale C1
- T9147 — Smart Scale P1
- T9148 — Smart Scale P2
- T9149 — Smart Scale P2 Pro
- T9150 — Smart Scale P3

The current official Home Assistant manifest lists exactly these eight local names. Primary upstream reference:

- `home-assistant/core/homeassistant/components/eufylife_ble/manifest.json`
- `bdr99/eufylife-ble-client/eufylife_ble_client/client.py`

## 2. Capability-driven entity exposure

Do not expose a common “everything” sensor set to every scale. Instead expose entities according to the model registry.

Raw/direct capabilities:

- live weight
- final weight
- impedance
- heart rate
- battery
- packet/protocol diagnostics

Calculated body-composition capability:

- enabled only if the model has a reliable same-session final weight and impedance pair
- P3: enabled by default because the raw protocol is hardware-verified by this project
- other models with upstream-validated impedance: calculation initially marked `experimental_cross_model` and disabled by default until explicitly enabled in options
- P2/P2 Pro: no impedance-based body composition until the real impedance encoding is solved

BMI technically needs only weight + height, but phase one deliberately keeps BMI inside the body-composition bundle rather than creating a special weight-only exception. This keeps behavior predictable and avoids implying that the rest of the composition data is available.

## 3. Support-level semantics

Create support level enum:

```python
class SupportLevel(StrEnum):
    VERIFIED = "verified"
    UPSTREAM_VALIDATED = "upstream_validated"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"
```

Support level is tracked **per capability**, not only per model. A model can therefore be upstream-validated for weight but experimental for impedance.

## 4. Transport policy

Use two transport modes:

```python
class TransportMode(StrEnum):
    ADVERTISEMENT = "advertisement"
    GATT = "gatt"
    ADVERTISEMENT_WITH_OPTIONAL_GATT = "advertisement_with_optional_gatt"
```

Rules:

- Prefer passive advertisement processing whenever the scale broadcasts enough data.
- Only open GATT connections for models that require them or for explicitly enabled extended metrics.
- All GATT sessions must use the Home Assistant Bluetooth/Bleak path so local adapters and active ESPHome Bluetooth proxies remain compatible.
- Never maintain an unnecessary permanent GATT connection to a scale.

## 5. Domain and public name

Before official HACS listing, rename the integration display name from `Eufy Smart Scale P3 BLE` to `Eufy Smart Scale BLE`.

Preferred domain change:

```text
eufy_p3_ble -> eufy_smart_scale_ble
```

This is a breaking change and should be released as a pre-1.0 minor release (recommended `0.3.0`). Because Home Assistant config-entry domains cannot be safely rewritten in place by a normal config-entry migration, do **not** maintain a second compatibility integration directory. Instead:

- document one-time migration for existing early users
- remove the old config entry before installing the renamed integration
- remove stale `custom_components/eufy_p3_ble` if HACS/manual installation leaves it behind
- restart Home Assistant
- install/add `Eufy Smart Scale BLE`
- preserve entity unique-id suffixes where practical, but document that entity registry entries may be recreated because the platform domain changes

If execution-time review determines preserving existing config entries is more important than a clean official domain, the fallback is to keep `eufy_p3_ble` internally and only rename the display name. Make that decision before Task 2 is merged; do not switch domains halfway through model implementation.

## 6. Privacy policy for community verification

Public issue attachments may include **safe diagnostics only**.

Safe diagnostics must exclude:

- Bluetooth address/MAC
- raw advertisement/notification bytes
- current or historical weight
- impedance
- heart rate
- age
- height
- sex
- profile mode
- timestamps precise enough to identify weighing behavior

For unknown-protocol reverse engineering, a future raw-capture mode may exist behind an explicit advanced option, but raw captures must never be requested for direct public upload through the normal issue template. The public model-verification template should ask users to attach sanitized diagnostics and describe only whether a feature worked.

---

# Target file structure

The current integration is concentrated under `custom_components/eufy_p3_ble/`. After the generalization, target this structure:

```text
custom_components/eufy_smart_scale_ble/
├── __init__.py
├── bluetooth.py
├── config_flow.py
├── const.py
├── device.py
├── diagnostics.py
├── manifest.json
├── model_registry.py
├── models.py
├── sensor.py
├── storage.py
├── composition_manager.py
├── body_composition.py
├── protocol_capture.py               # advanced/disabled by default, later task
├── protocols/
│   ├── __init__.py
│   ├── base.py
│   ├── p3.py
│   ├── c20.py
│   ├── onebyone.py                   # T9120/T9146/T9147 GATT family
│   ├── legacy_t9140.py
│   └── p2.py                         # T9148/T9149
└── translations/
    ├── en.json
    └── de.json
```

Tests:

```text
tests/
├── fixtures/
│   ├── builders.py                   # synthetic frame builders only
│   └── README.md                     # states all fixtures are synthetic
├── protocols/
│   ├── test_p3.py
│   ├── test_c20.py
│   ├── test_onebyone.py
│   ├── test_legacy_t9140.py
│   └── test_p2.py
├── test_model_registry.py
├── test_transport.py
├── test_device.py
├── test_config_flow.py
├── test_sensor.py
├── test_diagnostics.py
└── test_privacy_guards.py
```

Documentation:

```text
docs/
├── protocol-sources.md
├── support-matrix.md
├── model-verification.md
└── superpowers/plans/2026-08-24-eufy-multi-scale-support.md
```

GitHub community files:

```text
.github/
└── ISSUE_TEMPLATE/
    └── model_verification.yml
```

Responsibilities:

- `model_registry.py`: one source of truth for model names, protocol family, transport, and per-capability support.
- `protocols/*.py`: pure parsing/protocol logic; no Home Assistant entity code.
- `bluetooth.py`: transport orchestration and advertisement selection, not model-specific parsing.
- `device.py`: generic measurement-session state machine consuming normalized protocol events.
- `sensor.py`: capability-gated entity creation.
- `body_composition.py`: calculation only; no Bluetooth/model discovery logic.
- `diagnostics.py`: safe Home Assistant diagnostics.
- `protocol_capture.py`: optional advanced capture isolated from normal diagnostics.

---

# Normalized protocol interfaces

Create the following common types in `protocols/base.py` / `models.py`:

```python
class MeasurementPhase(StrEnum):
    LIVE = "live"
    LOCKED = "locked"
    IMPEDANCE = "impedance"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class MeasurementEvent:
    phase: MeasurementPhase
    weight_kg: float | None = None
    impedance_ohm: float | None = None
    heart_rate_bpm: int | None = None
    battery_percent: int | None = None
    sequence: int | None = None
    raw_packet: bytes | None = None


class AdvertisementParser(Protocol):
    def parse(
        self, manufacturer_data: Mapping[int, object]
    ) -> tuple[MeasurementEvent, ...]: ...


@dataclass(frozen=True, slots=True)
class GattProfile:
    notify_characteristics: tuple[str, ...]
    write_characteristics: tuple[str, ...]
    auth_characteristics: tuple[str, ...] = ()
    battery_characteristics: tuple[str, ...] = ()
```

Generic session state in `device.py` consumes `MeasurementEvent` and owns:

- current live weight
- last final weight
- current session impedance
- current session heart rate
- session timestamp
- last complete `BodyMeasurement`

Protocol parsers own model-specific duplicate/out-of-order handling when necessary. For P3, preserve the existing sequence-counter rules inside `protocols/p3.py`; do not force those semantics on other models.

---

# Model protocol matrix and implementation instructions

## T9150 — Eufy Smart Scale P3

**Initial project support level:** Verified for raw BLE protocol; body-composition algorithm remains experimental.

**Transport:** Advertisement only.

**Discovery:** local name `eufy T9150`.

**Current implementation source:** existing project code in `parser.py`, `bluetooth.py`, and `device.py`.

**Known packet facts already implemented:**

- manufacturer-data payload length: current parser accepts >= 19 bytes; known real packets are longer
- sequence: byte 6, unsigned 8-bit with wraparound
- status: byte 10
- weight: bytes 12..13, little-endian, `/ 100`
- heart-rate-present flag: byte 11 bit `0x80`
- heart rate: byte 15
- impedance: bytes 17..18, little-endian, `/ 10`
- extended P3 status phases already handled by this project

**Implementation approach:**

- Move existing P3-specific parsing into `protocols/p3.py` without semantic changes.
- Keep the sequence/newest-frame logic P3-specific.
- Convert existing `ScaleFrame` output into normalized `MeasurementEvent` objects.
- Preserve same-session impedance protection exactly.
- Preserve all current body-composition entities and persistence behavior.

**Do not change while generalizing:**

- P3 final-weight semantics
- P3 status ranking
- same-session impedance pairing
- current body-composition algorithm output
- persistence/recalculation behavior

**Synthetic tests required:**

- live -> locked -> impedance -> complete sequence
- stale packet rejected
- duplicate packet rejected
- sequence wraparound
- previous-session impedance never reused
- heart-rate flag validation
- invalid weight/impedance ranges rejected

**Primary sources:** project code; current project README/tests.

---

## T9130 — Eufy Smart Scale C20

**Initial support level:** Upstream Validated for weight/final weight; Upstream Validated for raw impedance and heart-rate decoding; cross-model body-composition calculation Experimental.

**Transport:** Advertisement only.

**Discovery:** local name `eufy T9130`.

**Strong upstream sources:**

1. `home-assistant/core` `eufylife_ble` manifest.
2. MIT `bdr99/eufylife-ble-client` — T9130 treated as advertisement-state device and weight parsing grouped with T9150.
3. `oliexdev/openScale` `EufyC20Handler.kt` — independent C20 advertisement parser showing weight, impedance and heart-rate flags/offsets. GPL reference only; do not copy implementation.

**Documented advertisement fields:**

- state/flags: byte 10
- weight available bit: `0x01`
- impedance available bit: `0x40`
- heart rate available bit: `0x80`
- weight: bytes 12..13, little-endian, `/ 100`
- heart rate: byte 15
- impedance: bytes 17..18, little-endian, `/ 10`
- official HA baseline considers `0x01` live weight and `0x05` final weight

**Implementation approach:**

Phase C20-A — weight parity with official Home Assistant:

- accept advertisement packets with sufficient length
- emit LIVE event for official live state
- emit COMPLETE/LOCKED final-weight event for official final state
- preserve latest final weight as restore sensor

Phase C20-B — richer fields:

- decode impedance/heart-rate flags independently from final-weight state
- permit an impedance or HR advertisement to enrich the active session after weight lock
- never combine a new session's weight with a previous session's impedance
- complete `BodyMeasurement` only when same-session final weight + impedance exist

**Body composition:**

- create raw impedance sensor normally once parser tests are complete
- expose P3-derived 14-metric calculation only behind `enable_experimental_cross_model_composition` option at first
- calculated entity attributes must include `algorithm_basis_model: "T9150"` and `model_support: "experimental"`
- later community verification can promote calculation support without changing raw parser support

**Synthetic tests required:**

- live C20 weight advertisement
- final C20 weight advertisement
- packet with impedance flag and synthetic impedance
- packet with heart-rate flag and synthetic heart rate
- multi-packet session merges weight + impedance + HR correctly
- stale previous-session impedance not reused
- packet without any known field ignored

---

## T9120 — Eufy Smart Scale A1

**Initial support level:** Upstream Validated for weight/final weight; Upstream Validated for GATT protocol family and impedance; body-composition calculation Experimental.

**Transport:** GATT required for measurement state.

**Discovery:** local name `eufy T9120`.

**Strong upstream sources:**

1. MIT `bdr99/eufylife-ble-client` model profile.
2. `oliexdev/openScale` OneByone handler — protocol-family cross-check, GPL reference only.
3. `KristianP26/ble-scale-sync` OneByone adapter — protocol-family cross-check, GPL reference only.

**Known GATT profile:**

- service family: `FFF0`
- notify: `FFF4`
- write: `FFF1`
- battery: standard `2A19`
- measurement frame begins `CF`

**Known measurement frame facts:**

- weight: bytes 3..4 little-endian `/ 100` kg
- final-weight flag in byte 9: `0x00` final
- over-limit status: byte 9 `0x02`
- impedance family evidence: `((byte2 << 8) + byte1) * 0.1` ohm
- upstream family evidence marks impedance absent when byte 9 is `0x01`

**Connection strategy:**

Baseline first:

- wake/discover from Bluetooth callback
- acquire best Home Assistant Bleak device for address
- establish short GATT connection
- subscribe to FFF4
- read battery from 2A19 if present
- parse weight frames
- disconnect after measurement completion or timeout

Extended protocol initialization only if required by testing/upstream behavior:

- mode/unit command on FFF1 (`FD 37 ... XOR` family)
- clock-sync command (`F1 <year><month><day><time>` family)
- do **not** request or clear scale history in the first implementation

Reason: history commands change device state and are unnecessary for Home Assistant live measurements.

**Impedance/body composition:**

- impedance parser may be included once synthetic parser tests match the documented Onebyone frame layout
- mark raw impedance Upstream Validated
- body-composition calculation stays experimental cross-model and opt-in until real A1 hardware/community confirmation

**Synthetic tests required:**

- FFF4 live frame
- final frame
- over-limit frame ignored as normal measurement
- valid/invalid impedance field
- connection timeout cleanup
- battery read
- reconnect after scale wakes again

---

## T9146 — Eufy Smart Scale C1

**Initial support level:** Upstream Validated for advertisement weight/final weight; GATT impedance Upstream Validated but optional; body-composition calculation Experimental.

**Transport:** Advertisement for normal weight; optional GATT for extended metrics.

**Discovery:** local name `eufy T9146`.

**Strong upstream sources:** MIT `bdr99/eufylife-ble-client`; Onebyone family cross-checks in openScale/ble-scale-sync.

**Advertisement layout from official client:**

- manufacturer payload expected length: 18 bytes
- byte 4 begins embedded `CF` frame
- embedded frame uses XOR checksum
- extract embedded 11-byte frame from advertisement
- weight: embedded frame bytes 3..4, little-endian `/ 100`
- final flag: embedded frame byte 9 `0x00`
- over-limit: embedded frame byte 9 `0x02`

**Checksum:** XOR of all embedded-frame bytes except final checksum byte; final byte equals XOR result.

**Implementation approach:**

Default mode:

- parse advertisements only
- live/final weight without opening GATT
- this keeps C1 proxy-friendly and low-overhead

Optional extended mode:

- use Onebyone GATT profile FFF1/FFF4 and 2A19 battery
- decode raw impedance
- do not connect if user has not enabled extended metrics

**Body composition:** experimental cross-model opt-in only when same-session impedance was obtained.

**Synthetic tests required:**

- correct checksum accepted
- bad checksum rejected
- final and non-final advertisement states
- optional GATT impedance session does not overwrite weight from another session

---

## T9147 — Eufy Smart Scale P1

**Initial support level:** Upstream Validated for advertisement weight/final weight; GATT impedance Upstream Validated but optional; body-composition calculation Experimental.

**Transport:** Advertisement for normal weight; optional GATT for extended metrics.

**Discovery:** local name `eufy T9147`.

**Protocol:** Same official advertisement and Onebyone GATT family as T9146.

**Implementation approach:**

- reuse the same pure `OnebyoneAdvertisementParser` / `OnebyoneGattParser` used by T9146
- keep a distinct model registry entry so support status and future model-specific quirks can diverge without parser forks
- never infer model from GATT UUIDs alone when local name is available; generic FFFx UUIDs can collide with unrelated scales

**Body composition:** experimental cross-model opt-in only.

**Synthetic tests required:**

- registry selects T9147 correctly
- same protocol vectors as T9146 produce correct normalized events
- capability matrix remains model-specific despite shared parser

---

## T9140 — original Eufy Smart Scale

**Initial support level:** Upstream Validated for dynamic/final weight; Experimental for impedance because multiple characteristic families/firmware variants exist; body composition Experimental and off by default.

**Transport:** GATT required.

**Discovery:** local name `eufy T9140`.

**Primary compatible sources:**

1. MIT `bdr99/eufylife-ble-client` model profile and weight parser.
2. MIT `cbondurant/eufy-protocol-reversal` for protocol-state interpretation and impedance events.
3. openScale issues/handlers as behavioral cross-check only.

**Candidate GATT characteristic families from official client:**

Notify candidates:

- `4143f7b2-5300-4900-4700-414943415245`
- `4143f6b2-5300-4900-4700-414943415245`
- `0000ffb2-0000-1000-8000-00805f9b34fb`

Write candidates:

- matching `...b1` variants
- standard battery `2A19`

**Weight frame behavior:**

- dynamic state terminator/status: `0xCE`
- stable/final state: `0xCA`
- weight: bytes 2..3 big-endian `/ 10` kg

**Multiplexed-notification behavior:**

Official client receives some 16/17-byte notifications beginning with `AC 02` and splits them into smaller logical frames before parsing. Implement a pure splitter first, then feed each logical frame into parser.

**Impedance evidence from MIT reverse-engineering:**

- `0xCB` family marks impedance process
- subtype indicates start/result
- result uses 16-bit value in designated bytes

Do not expose this as normal supported impedance until community hardware confirms the chosen characteristic family and result scaling.

**Implementation approach:**

- discover services dynamically
- choose first available known notify/write pair as a matched pair; never mix F6 notify with F7 write
- subscribe
- parse CE dynamic weights
- parse CA stable weight as final
- optionally observe CB impedance event into internal experimental field
- read battery if 2A19 exists
- disconnect after final/timeout

**Synthetic tests required:**

- every characteristic-family matcher
- 16-byte split
- 17-byte split
- CE live weight
- CA final weight
- CB start/result parsing
- no impedance entity when experimental feature disabled
- timeout/disconnect cleanup

---

## T9148 — Eufy Smart Scale P2

**Initial support level:** Upstream Validated for advertisement weight/final weight; authenticated GATT flow Upstream Validated but not needed for baseline; impedance UNSUPPORTED for normal entities until encoding is solved.

**Transport:** Advertisement baseline; optional authenticated GATT research path.

**Discovery:** local name `eufy T9148`.

**Strong sources:**

- MIT `bdr99/eufylife-ble-client`
- openScale/ble-scale-sync as GPL behavioral cross-checks only

**Advertisement baseline:**

- payload length approximately 19 bytes
- marker `CF` at byte 6
- weight: bytes 9..10 little-endian `/ 100`
- final flag: byte 15 `0x00`
- emit live weight for non-final frames and final weight when flag becomes final

**GATT profile:**

- service `FFF0`
- write `FFF1`
- measurement notify `FFF2`
- authentication notify `FFF4`
- battery `2A19` where available

**Authentication flow:**

- key: MD5 of normalized uppercase MAC text without separators
- IV: ASCII `0000000000000000`
- C0/C1/C2/C3 segmented authentication
- AES-128-CBC/PKCS7
- C3 status byte zero indicates success

Implementation must be independently written from protocol facts; prefer the MIT upstream Python implementation as primary source.

**FFF2 weight notification:**

- 16-byte frame
- begins `CF`
- weight: bytes 6..7 little-endian `/ 100`
- final flag: byte 12 `0x00`

**Critical impedance rule:**

The three bytes often interpreted as a 24-bit impedance value are **not a verified usable resistance**. Real hardware reports values in the millions when treated that way, while upstream maintainers explicitly keep the decode disabled. Therefore:

- do not create an impedance sensor
- do not feed that field into body-composition formulas
- do not label the field as ohms in diagnostics
- if retained for research, call it `opaque_composition_field` internally and exclude it from standard diagnostics

**Body composition:** unavailable until real impedance decode exists.

**Synthetic tests required:**

- advertisement live/final weight
- FFF2 live/final weight
- auth segmentation checksum
- C1 reassembly
- C3 success/failure
- explicit test asserting opaque 24-bit field does **not** populate `impedance_ohm`

---

## T9149 — Eufy Smart Scale P2 Pro

**Initial support level:** Upstream Validated for weight/final weight and heart rate; authenticated GATT flow Upstream Validated; impedance UNSUPPORTED for normal entities until encoding is solved.

**Transport:** Advertisement baseline; optional authenticated GATT research path.

**Discovery:** local name `eufy T9149`.

**Protocol family:** Same P2 auth/GATT structure as T9148.

**Advertisement heart-rate evidence from official client:**

After normalizing from the embedded frame:

- HR validity encoded in status/flag bits
- HR value carried in the advertisement field used by official `eufylife-ble-client`
- expose heart rate only for T9149, not T9148

**Implementation approach:**

- share `P2AdvertisementParser` and `P2GattProtocol` with T9148
- registry capability turns heart-rate entity on only for T9149
- no impedance sensor
- no impedance-based body-composition entities

**Known real-world warning:** independent community testing demonstrated that the naïve 24-bit field decode produces multi-million-ohm values. Treat the field as opaque, exactly as for T9148.

**Synthetic tests required:**

- T9149 HR-present advertisement
- invalid/zero HR ignored
- T9148 does not expose HR despite shared parser
- opaque field never becomes impedance

---

# Initial support matrix after implementation

| Model | Weight/live/final | Heart rate | Raw impedance | Body composition | Transport |
|---|---|---|---|---|---|
| T9120 A1 | Upstream Validated | Unsupported | Upstream Validated | Experimental opt-in | GATT |
| T9130 C20 | Upstream Validated | Upstream Validated | Upstream Validated | Experimental opt-in | Advertisement |
| T9140 Smart Scale | Upstream Validated | Unsupported | Experimental/off | Experimental/off | GATT |
| T9146 C1 | Upstream Validated | Unsupported | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| T9147 P1 | Upstream Validated | Unsupported | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| T9148 P2 | Upstream Validated | Unsupported | Unsupported/opaque research field | Unavailable | Advertisement; optional auth GATT research |
| T9149 P2 Pro | Upstream Validated | Upstream Validated | Unsupported/opaque research field | Unavailable | Advertisement; optional auth GATT research |
| T9150 P3 | Verified | Verified | Verified | Experimental algorithm, enabled | Advertisement |

---

# Implementation tasks

## Task 1: Lock current P3 behavior with architecture-neutral regression tests

**Files:**
- Modify: `tests/test_parser.py`
- Modify: `tests/test_device.py`
- Modify: `tests/test_sensor.py`
- Create: `tests/fixtures/builders.py`
- Create: `tests/fixtures/README.md`

**Interfaces:**
- Consumes: current P3 parser/device/sensor behavior.
- Produces: synthetic regression fixtures that future refactors must preserve.

- [ ] **Step 1: Add synthetic packet builders**

Create builders using only chosen synthetic numbers, never copied real captures:

```python
def build_p3_packet(
    *,
    sequence: int,
    status: int,
    weight_hundredths: int,
    impedance_tenths: int = 0,
    heart_rate: int | None = None,
) -> bytes:
    data = bytearray(23)
    data[6] = sequence
    data[10] = status
    data[12:14] = weight_hundredths.to_bytes(2, "little")
    if impedance_tenths:
        data[17:19] = impedance_tenths.to_bytes(2, "little")
    if heart_rate is not None:
        data[11] |= 0x80
        data[15] = heart_rate
    return bytes(data)
```

- [ ] **Step 2: Add explicit test proving all committed fixtures are synthetic builders**

`tests/fixtures/README.md` must state no real-world packet captures may be committed.

- [ ] **Step 3: Run current P3 tests**

Run:

```bash
pytest tests/test_parser.py tests/test_device.py tests/test_sensor.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures tests/test_parser.py tests/test_device.py tests/test_sensor.py
git commit -m "test: lock P3 behavior with synthetic fixtures"
```

---

## Task 2: Rename/generalize the integration before adding models

**Files:**
- Rename directory: `custom_components/eufy_p3_ble` -> `custom_components/eufy_smart_scale_ble`
- Modify all imports/tests referencing old domain
- Modify: `hacs.json`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces domain `eufy_smart_scale_ble` and display name `Eufy Smart Scale BLE`.

- [ ] **Step 1: Write failing repository-readiness tests for new domain/name**

Add assertions that exactly one integration exists and its manifest domain/name are generic.

- [ ] **Step 2: Run readiness test and verify RED**

```bash
pytest tests/test_repository_readiness.py -v
```

Expected: failure on old domain/name.

- [ ] **Step 3: Rename integration directory and update imports**

Do not leave a second compatibility directory.

- [ ] **Step 4: Remove duplicate hard-coded `VERSION` constant from `const.py`**

Manifest/pyproject/changelog remain the authoritative version sources. Avoid another stale `const.VERSION` drift.

- [ ] **Step 5: Add one-time migration instructions to README/changelog**

Explain removal/re-add requirement caused by domain change.

- [ ] **Step 6: Run full suite**

```bash
pytest
ruff format --check .
ruff check .
mypy
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: generalize integration domain and naming"
```

---

## Task 3: Add model registry and per-capability support levels

**Files:**
- Create: `custom_components/eufy_smart_scale_ble/model_registry.py`
- Modify: `models.py`
- Modify: `const.py`
- Create: `tests/test_model_registry.py`

**Interfaces:**
- Produces: `SUPPORTED_MODELS`, `ScaleModelDefinition`, `Capability`, `SupportLevel`, `TransportMode`.

- [ ] **Step 1: Write failing registry tests**

```python
def test_all_official_eufylife_models_are_registered():
    assert set(SUPPORTED_MODELS) == {
        "eufy T9120",
        "eufy T9130",
        "eufy T9140",
        "eufy T9146",
        "eufy T9147",
        "eufy T9148",
        "eufy T9149",
        "eufy T9150",
    }
```

Add tests for T9150 verified impedance and T9148 unsupported impedance.

- [ ] **Step 2: Implement enums/dataclasses**

```python
@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    level: SupportLevel
    enabled_by_default: bool


@dataclass(frozen=True, slots=True)
class ScaleModelDefinition:
    model_id: str
    display_name: str
    protocol_family: str
    transport: TransportMode
    capabilities: Mapping[Capability, CapabilityDefinition]
```

- [ ] **Step 3: Populate all eight models according to the support matrix**

- [ ] **Step 4: Run tests and commit**

```bash
pytest tests/test_model_registry.py -v
git add custom_components/eufy_smart_scale_ble/model_registry.py custom_components/eufy_smart_scale_ble/models.py tests/test_model_registry.py
git commit -m "feat: add Eufy scale model capability registry"
```

---

## Task 4: Introduce normalized measurement events and generic session state

**Files:**
- Create: `protocols/base.py`
- Modify: `device.py`
- Modify: `models.py`
- Modify: `composition_manager.py`
- Modify: `tests/test_device.py`

**Interfaces:**
- Consumes: `MeasurementEvent`.
- Produces: generic `EufyScaleDevice.process_event(event)` state updates.

- [ ] **Step 1: Write failing device tests using normalized events**

Test LIVE -> COMPLETE, impedance enrichment, and old impedance rejection.

- [ ] **Step 2: Implement `MeasurementEvent` and generic session handling**

Do not include P3 status codes in generic state.

- [ ] **Step 3: Keep `BodyMeasurement` creation conditional on same-session final weight + impedance**

- [ ] **Step 4: Run device/composition tests**

```bash
pytest tests/test_device.py tests/test_composition_manager.py -v
```

- [ ] **Step 5: Commit**

```bash
git commit -am "refactor: normalize scale measurement session events"
```

---

## Task 5: Move P3 into protocol module without changing behavior

**Files:**
- Create: `protocols/p3.py`
- Modify: `bluetooth.py`
- Delete or reduce old `parser.py` after migration
- Create: `tests/protocols/test_p3.py`

**Interfaces:**
- Produces: `P3AdvertisementParser.parse(...) -> tuple[MeasurementEvent, ...]`.

- [ ] **Step 1: Copy tests, not implementation, into new protocol-test shape**
- [ ] **Step 2: Run and verify failure because parser does not exist**
- [ ] **Step 3: Move current pure parsing/sequence logic into `protocols/p3.py`**
- [ ] **Step 4: Adapt output to normalized events**
- [ ] **Step 5: Run complete P3 regression suite**
- [ ] **Step 6: Commit**

---

## Task 6: Generalize Bluetooth discovery and config flow for eight models

**Files:**
- Modify: `manifest.json`
- Modify: `config_flow.py`
- Modify: `__init__.py`
- Modify: translations
- Modify: `tests/test_config_flow.py`
- Modify: `tests/test_init.py`

**Interfaces:**
- Consumes: `SUPPORTED_MODELS`.
- Produces: entries storing the exact discovered `CONF_MODEL`.

- [ ] **Step 1: Add failing discovery tests for all eight local names**
- [ ] **Step 2: Add all eight Bluetooth matchers to manifest**
- [ ] **Step 3: Replace hard-coded `MODEL_ID` checks with registry lookup**
- [ ] **Step 4: Entry title comes from model registry display name**
- [ ] **Step 5: Manual setup lists every currently discovered supported model**
- [ ] **Step 6: Unknown Eufy local names abort as unsupported**
- [ ] **Step 7: Run config/init tests and commit**

---

## Task 7: Capability-gate sensors and body-composition options

**Files:**
- Modify: `sensor.py`
- Modify: `config_flow.py`
- Modify: `composition_manager.py`
- Modify translations
- Modify: `tests/test_sensor.py`
- Modify: `tests/test_config_flow.py`

**Interfaces:**
- Consumes: model capabilities.
- Produces: only valid entities for each model.

- [ ] **Step 1: Write failing entity-count tests per representative model**

Examples:

- T9148: weight/live only, no impedance/body-comp
- T9149: weight/live + HR, no impedance/body-comp
- T9150: current full entity set

- [ ] **Step 2: Add `required_capability` to entity descriptions**
- [ ] **Step 3: Add `enable_experimental_cross_model_composition` option only when relevant**
- [ ] **Step 4: Prevent profile options from appearing on weight-only models unless an experimental composition path exists**
- [ ] **Step 5: Run tests and commit**

---

## Task 8: Implement C20/T9130 advertisement protocol

**Files:**
- Create: `protocols/c20.py`
- Create: `tests/protocols/test_c20.py`
- Modify: `model_registry.py`
- Modify: `bluetooth.py`

**Interfaces:**
- Produces `C20AdvertisementParser`.

- [ ] **Step 1: Add synthetic C20 builder to `tests/fixtures/builders.py`**
- [ ] **Step 2: Write RED tests for weight/final, impedance flag, HR flag**
- [ ] **Step 3: Implement official HA weight/final semantics first**
- [ ] **Step 4: Add impedance/HR bit decoding from independent protocol evidence**
- [ ] **Step 5: Verify same-session merge through device test**
- [ ] **Step 6: Run full suite + HACS/Hassfest before merge**
- [ ] **Step 7: Update support matrix docs and commit**

---

## Task 9: Implement shared C1/P1 advertisement parser

**Files:**
- Create/extend: `protocols/onebyone.py`
- Create: `tests/protocols/test_onebyone.py`
- Modify: `model_registry.py`
- Modify: `bluetooth.py`

**Interfaces:**
- Produces `OnebyoneAdvertisementParser` for T9146/T9147.

- [ ] **Step 1: Build synthetic 11-byte CF frame + XOR checksum helper**
- [ ] **Step 2: Embed it in synthetic 18-byte advertisement fixture**
- [ ] **Step 3: RED tests for valid/bad checksum, live/final, over-limit**
- [ ] **Step 4: Implement parser**
- [ ] **Step 5: Confirm T9146 and T9147 share parser but have separate registry entries**
- [ ] **Step 6: Commit**

---

## Task 10: Add generic short-lived GATT session transport

**Files:**
- Create: `gatt.py` or `transport.py`
- Modify: `__init__.py`
- Modify: `bluetooth.py`
- Create: `tests/test_transport.py`

**Interfaces:**
- Produces `EufyGattSession` that resolves model-specific characteristics, subscribes, emits events, reads battery, and always disconnects.

- [ ] **Step 1: Write mocked Bleak lifecycle test**

Verify connect -> subscribe -> event -> disconnect even on parser exception.

- [ ] **Step 2: Implement connection through HA Bluetooth/Bleak device**
- [ ] **Step 3: Add timeout and idempotent cleanup**
- [ ] **Step 4: Prevent concurrent duplicate connections for same entry**
- [ ] **Step 5: Run transport tests and commit**

---

## Task 11: Implement A1/C1/P1 Onebyone GATT enrichment

**Files:**
- Modify: `protocols/onebyone.py`
- Modify: `model_registry.py`
- Modify: `gatt.py`
- Modify: `tests/protocols/test_onebyone.py`

**Interfaces:**
- Produces Onebyone GATT parser and optional initialization sequence.

- [ ] **Step 1: RED tests for CF GATT weight and impedance**
- [ ] **Step 2: Implement FFF4 notification parser**
- [ ] **Step 3: Add battery read from 2A19**
- [ ] **Step 4: Add conservative mode/unit + clock initialization only if required**
- [ ] **Step 5: Explicitly omit history request/clear commands**
- [ ] **Step 6: A1 uses GATT by default; C1/P1 use it only for extended metrics**
- [ ] **Step 7: Run model-specific entity tests and commit**

---

## Task 12: Implement T9140 legacy GATT protocol

**Files:**
- Create: `protocols/legacy_t9140.py`
- Create: `tests/protocols/test_legacy_t9140.py`
- Modify: `model_registry.py`
- Modify: `gatt.py`

**Interfaces:**
- Produces dynamic/final weight events; optional experimental impedance event.

- [ ] **Step 1: RED tests for characteristic-family resolution**
- [ ] **Step 2: RED tests for multiplex frame splitting**
- [ ] **Step 3: Implement CE live and CA final parsing**
- [ ] **Step 4: Implement CB impedance parsing behind experimental capability flag**
- [ ] **Step 5: Verify impedance entity absent by default**
- [ ] **Step 6: Run tests and commit**

---

## Task 13: Implement P2/P2 Pro advertisement baseline

**Files:**
- Create: `protocols/p2.py`
- Create: `tests/protocols/test_p2.py`
- Modify: `model_registry.py`
- Modify: `bluetooth.py`

**Interfaces:**
- Produces P2 advertisement events with weight/final and optional T9149 HR.

- [ ] **Step 1: RED synthetic tests for 19-byte advertisements**
- [ ] **Step 2: Implement weight/final parser**
- [ ] **Step 3: Add T9149 HR gating**
- [ ] **Step 4: Add explicit regression proving unknown 24-bit field is not impedance**
- [ ] **Step 5: Commit**

---

## Task 14: Implement P2/P2 Pro authenticated GATT as research-capable transport

**Files:**
- Extend: `protocols/p2.py`
- Extend: `gatt.py`
- Extend: `tests/protocols/test_p2.py`

**Interfaces:**
- Produces C0/C1/C2/C3 handshake and FFF2 weight parsing.

- [ ] **Step 1: Write pure crypto/segmentation tests with generated synthetic MAC placeholder**

Use a clearly synthetic address such as generated bytes inside test helper; do not commit a real device MAC.

- [ ] **Step 2: Implement MD5 key derivation, AES-CBC, segmentation checksum**
- [ ] **Step 3: Implement C1 reassembly and C3 status handling**
- [ ] **Step 4: Implement FFF2 weight/final parser**
- [ ] **Step 5: Keep composition field opaque and hidden**
- [ ] **Step 6: Add conservative pacing between auth segments**
- [ ] **Step 7: Keep this path disabled unless future functionality needs it**
- [ ] **Step 8: Commit**

---

## Task 15: Add privacy-safe Home Assistant diagnostics

**Files:**
- Create: `diagnostics.py`
- Create: `tests/test_diagnostics.py`
- Create: `tests/test_privacy_guards.py`

**Interfaces:**
- Produces `async_get_config_entry_diagnostics` safe report.

Safe example structure:

```python
{
    "model": "T9149",
    "protocol_family": "p2",
    "transport": "advertisement",
    "capabilities": {"weight": "upstream_validated", "impedance": "unsupported"},
    "runtime": {
        "advertisements_seen": 42,
        "accepted_events": 8,
        "packet_lengths_seen": [19],
        "parser_statuses_seen": ["live", "complete"],
    },
}
```

- [ ] **Step 1: RED test asserts forbidden fields are absent**

Forbidden keys/values include address, raw packets, profile, measurement values.

- [ ] **Step 2: Implement safe diagnostics**
- [ ] **Step 3: Add repository privacy guard against concrete MAC literals in docs/tests**
- [ ] **Step 4: Commit**

---

## Task 16: Add explicit advanced protocol-capture architecture without enabling public raw uploads

**Files:**
- Create: `protocol_capture.py`
- Modify: `config_flow.py`
- Modify translations
- Create: `tests/test_protocol_capture.py`

**Interfaces:**
- Produces disabled-by-default in-memory capture recorder.

Rules:

- default OFF
- standard diagnostics never include raw capture
- explicit advanced option required
- bounded ring buffer
- automatic clear on reload/restart
- no persistence
- UI warning that raw BLE may encode personal measurement data
- public issue template must not ask for raw capture

- [ ] **Step 1: RED tests proving capture is off and empty by default**
- [ ] **Step 2: Implement bounded in-memory recorder**
- [ ] **Step 3: Prove recorder data never enters standard diagnostics**
- [ ] **Step 4: Add warning copy**
- [ ] **Step 5: Commit**

---

## Task 17: Add public support matrix and protocol-source documentation

**Files:**
- Create: `docs/support-matrix.md`
- Create: `docs/protocol-sources.md`
- Modify: `README.md`

`docs/protocol-sources.md` must list sources and licenses by model. Suggested source set:

- Home Assistant core `eufylife_ble` integration
- `bdr99/eufylife-ble-client` — MIT, primary implementation reference
- `cbondurant/eufy-protocol-reversal` — MIT, T9140 reference
- `oliexdev/openScale` — GPL, behavioral/reference-only
- `KristianP26/ble-scale-sync` — GPL, behavioral/reference-only and real-hardware issue evidence

Do not paste real captures or measurements into this document.

- [ ] **Step 1: Document support-level definitions**
- [ ] **Step 2: Add the eight-model matrix**
- [ ] **Step 3: Clearly distinguish raw protocol support from body-composition formula validation**
- [ ] **Step 4: Add “How to help verify a model” link**
- [ ] **Step 5: Commit**

---

## Task 18: Add privacy-safe model-verification issue template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/model_verification.yml`
- Create: `docs/model-verification.md`

Template fields:

- model from dropdown
- integration version
- Home Assistant version
- Bluetooth path: local adapter / ESPHome proxy
- which capability was tested
- whether weight/final/HR/impedance entity behaved as expected
- safe diagnostics attachment

Required checkbox:

> I verified that my attachment does not contain a Bluetooth/MAC address, raw BLE payload, weight, impedance, heart rate, body profile, or other personal measurement data.

Do not request screenshots of body-composition pages or real raw logs in the default public template.

- [ ] **Step 1: Add template**
- [ ] **Step 2: Add model-verification documentation**
- [ ] **Step 3: Validate YAML and commit**

---

## Task 19: Full cross-model integration tests

**Files:**
- Modify/create representative integration tests under `tests/`

Scenarios required:

1. P3 passive complete session with full raw fields.
2. C20 passive weight + impedance + HR.
3. C1 passive weight only with no GATT option.
4. C1 optional GATT enrichment.
5. A1 mandatory GATT session.
6. T9140 mandatory GATT dynamic -> stable.
7. P2 passive weight only.
8. P2 Pro passive weight + HR.
9. Unsupported impedance never creates composition entities.
10. Restart restores only legitimate stored measurements.
11. Model change cannot occur silently for an existing config entry.
12. Diagnostics never expose forbidden data.

- [ ] **Step 1: Add tests one scenario at a time**
- [ ] **Step 2: Run each test RED before implementation adjustments**
- [ ] **Step 3: Run full suite**

```bash
pytest --cov=custom_components/eufy_smart_scale_ble --cov-branch --cov-report=term-missing
ruff format --check .
ruff check .
mypy
python -m compileall -q custom_components tests
```

- [ ] **Step 4: Confirm HACS workflow green**
- [ ] **Step 5: Confirm Hassfest workflow green**
- [ ] **Step 6: Commit final integration-test updates**

---

## Task 20: Release strategy and staged rollout

Do not merge every protocol family into one giant unreviewable PR.

Recommended sequence:

1. Architecture/domain generalization with P3-only behavior preserved.
2. C20.
3. C1/P1 passive support.
4. A1 + optional C1/P1 Onebyone GATT.
5. T9140.
6. P2/P2 Pro passive support.
7. Optional P2 auth GATT research path.
8. Diagnostics/community verification tooling.

Release recommendation:

- `0.3.0`: generic integration/domain architecture and P3 parity
- subsequent minor/patch pre-1.0 releases after stable protocol-family additions
- every release must keep manifest, pyproject and changelog synchronized
- every changelog entry stays generic; no real measurement/test values

Before each release:

- [ ] full Tests workflow green
- [ ] HACS workflow green
- [ ] Hassfest green
- [ ] support matrix updated
- [ ] privacy diagnostics test green
- [ ] no experimental capability accidentally enabled by default
- [ ] GitHub Release created, not tag-only

---

# Definition of done for official HACS-submission readiness

The multi-model project is considered ready for a future HACS default-store PR only when:

- all eight official Home Assistant EufyLife model IDs are discoverable
- P3 remains hardware-verified and regression-safe
- every other model has at least reliable upstream-validated weight/final-weight support
- P2 Pro HR is supported without exposing false impedance
- unsupported/experimental fields are accurately gated
- body-composition entities only appear when a reliable same-session impedance exists
- safe diagnostics are available
- public model-verification workflow exists
- README/support matrix clearly communicate verification levels
- full tests, HACS and Hassfest are green
- no real personal measurements/captures exist in repository history introduced by this work

---

# Research sources to re-check immediately before implementation

Primary compatible sources:

- https://github.com/home-assistant/core/tree/dev/homeassistant/components/eufylife_ble
- https://github.com/bdr99/eufylife-ble-client
- https://github.com/cbondurant/eufy-protocol-reversal

Behavioral cross-check sources only; do not copy implementation into this MIT project:

- https://github.com/oliexdev/openScale
- https://github.com/KristianP26/ble-scale-sync

Specific known risk to re-check before P2/P2 Pro implementation:

- `KristianP26/ble-scale-sync` issue #289 and its resolution: naïve 24-bit P2/P2-Pro field is not a usable impedance value.

Specific known risk to re-check before T9140 implementation:

- current openScale T9140 compatibility reports and variant characteristic families.

---

# Self-review of this plan

- Spec coverage: all eight target models have explicit transport, protocol evidence, entity policy, and tests.
- Privacy coverage: standard diagnostics, public issue flow, synthetic fixtures, and raw-capture separation are explicitly specified.
- License coverage: MIT-compatible sources are primary; GPL sources are reference-only.
- Type consistency: model registry -> parser/transport -> normalized event -> generic device -> capability-gated sensor pipeline is consistent across tasks.
- No body-composition fallback uses fabricated impedance or BMI-derived body-fat values.
- P3 behavior is frozen before refactoring so multi-model work cannot silently regress the original use case.
