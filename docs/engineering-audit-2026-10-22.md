# Engineering audit — 2026-10-22

Audited base: [`6ac4c0ce7e3ab6ae7c45ce74cd4bbf982e2c654a`](https://github.com/Skriipt/eufy-smart-scale-ble/tree/6ac4c0ce7e3ab6ae7c45ce74cd4bbf982e2c654a), version 0.3.4.
Scope: all integration Python modules, all tests, fixtures, translations/metadata,
CI workflows, recent changes, README, and protocol/support documentation.
All validation used synthetic data and mocked Bluetooth. No scale or live Home
Assistant installation was contacted. Only P3/T9150 retains project hardware
verification; this audit does not promote any model or capability.

The supplied review branch initially contained the unrelated GitHub profile
repository. Only the clean review branch's starting point was replaced with
the requested repository's fetched commit. The existing local main
and shared origin configuration were left unchanged.

## Confirmed defects fixed

Locations below refer to the reviewed base, so they remain useful after line
numbers move. P1 indicates incorrect measurement association or transport work
surviving unload; P2 indicates significant lifecycle, persistence or privacy
defects. Test names identify reproducible acceptance criteria in this patch.

### P1 — A changed locked weight inherited the preceding impedance

`device.py:109-131,174-184`: a locked 60 kg/500 ohm event followed five seconds
later by a locked 80 kg event produced an invented 80 kg/500 ohm pair with the
first event's timestamp. The implementation only recognized selected textual
phase transitions as a new session. It now discards pending pairing inputs when
the finalized weight changes, including when the intermediate live phase is lost.
The previous completed composition remains available until a new pair exists.

Proof: `test_different_final_weight_never_reuses_previous_impedance`.

### P1 — GATT work could complete after unload or retain a failed subscription

`gatt.py:57-96,123-129,195-207`: scheduled connection attempts were not retained,
and stop only disconnected a client that had already been assigned. Releasing a
blocked connection after stop subscribed to notifications on an orphaned client.
A `start_notify` failure also left the connected client in place until its timer
expired. Setup lacked an integration-level timeout, and an old client's
disconnect callback could clear a newer client and cancel its timer.

The transport now cancels and awaits pending setup, permanently rejects requests
after unload/shutdown, cleans up setup errors/cancellation, guards callbacks by
client identity, bounds setup and disconnect cleanup, and keeps ordinary timed
disconnects reconnectable. Concurrent timeout/unload cannot cancel cleanup twice.
HA shutdown explicitly closes the transport.

Proof: `test_stop_cancels_pending_connection`,
`test_failed_notify_disconnects_immediately`,
`test_old_disconnect_callback_cannot_clear_new_connection`,
`test_connection_setup_is_bounded`,
`test_notify_battery_and_late_callback_lifecycle`,
`test_timed_disconnect_allows_a_later_connection`,
`test_concurrent_timeout_and_unload_do_not_cancel_client_cleanup`, and
`test_shutdown_stops_gatt`.

### P2 — Auxiliary updates and C20 status labels changed session boundaries

`device.py:75-80,174-184`; `gatt.py:133-140`: a battery read was represented as a
LIVE event and erased a locked weight before an impedance-only notification.
C20 reports labels such as `0x01` and `0xc5`, so comparisons with the literal
strings `live` and `locked` reset consecutive live packets and re-timestamped
duplicate final packets. Pairing now uses the normalized phase; battery-only
and heart-rate-only updates do not alter the measurement session.

Proof: `test_battery_read_does_not_interrupt_weight_impedance_pair`,
`test_protocol_status_text_does_not_define_session_boundaries`, and
`test_duplicate_final_does_not_change_measurement_timestamp`.

### P2 — Restoration could roll back a newer weight-only result

`device.py:31-39`; `sensor.py:324-328`: the saved composition pair initialized
raw device state. After RestoreSensor loaded a newer 80 kg reading, applying
an older 60 kg composition pair overwrote it; subsequent live updates repeated
the rollback. Raw entities now restore through Home Assistant's native sensor
storage independently of the last complete composition pair.

Proof: `test_old_composition_pair_does_not_replace_restored_weight` covers
startup, the next live event, and a new finalized reading. If HA has no raw
sensor restore data, those raw values remain unknown until received again;
composition restoration still works from its own store.

### P2 — Concurrent persistence could leave an older measurement on disk

`__init__.py:84-97`; `storage.py:74-97`: each save created a separate Store, so
Store's per-instance write lock could not order concurrent writes to the same
file. Saves were also ordinary HA tasks rather than tasks owned by the entry.
A per-entry lock now serializes writes; config-entry task tracking makes unload
wait for them within HA's lifecycle wait limit.

Proof: `test_persistence_is_ordered_and_unload_waits_for_it` blocks the older
write while a newer measurement arrives and an unload starts.

### P2 — Passive proxies were excluded and live availability was not published

`manifest.json:4-28`; `__init__.py:157-164`; `sensor.py:339-345,376-383`:
Home Assistant defaults omitted `connectable` matchers and presence queries to
true. Advertisement models therefore missed updates from non-connectable
proxies. In addition, the live/status entities only wrote state after accepted
measurement events, so merely becoming unavailable did not update their HA state.

Advertisement-capable models now accept passive-only sources at discovery,
runtime subscription and availability checks. GATT-only models still require a
connectable source. Live/status entities subscribe to disappearance and return
events independently of whether a measurement is accepted. Historical completed
measurements intentionally remain available while the scale sleeps.

Proof: `test_passive_proxy_matches_runtime_subscription` and
`test_passive_presence_loss_and_return_publish_state`.

### P2 — Private data escaped its intended storage and logging boundaries

`sensor.py:432-453` copied sex, age, height and profile mode into every calculated
entity's attributes, making them available through normal entity-state access
and Recorder history. These profile attributes have been removed. Measurement
inputs and their timestamps remain visible, as documented.

`storage.py:77-81` used Store's default non-private mode. HA's actual file writer
sets such files to `0644`; new writes now use `0600`. Entry deletion now removes
the integration-owned store. Old files acquire the stricter mode on their next
write; no historical Recorder records or backups are purged.

`gatt.py:90-94`; `__init__.py:57-59,88-90,150-155` logged arbitrary exception
strings, which BLE/backend errors can populate with identifiers or payloads.
These paths now log the exception class only and deduplicate advertisement
errors by class. The capture buffer is explicitly cleared on unload.

Proof: `test_connection_error_does_not_log_private_details`,
`test_runtime_exception_does_not_log_private_details`,
`test_measurement_file_is_private_and_removed_with_entry`,
`test_unload_clears_capture`, and calculated-sensor attribute assertions.

## Remaining findings and hardware-dependent questions

1. **P2, proven software limitation; hardware incidence unverified — ordering
   outside P3.** `protocols/c20.py:21-59` emits every candidate in dictionary
   order; OneByone and P2 select the first valid candidate
   (`protocols/onebyone.py:45-52`, `bluetooth.py:29-35`). C20 synthetic final
   payloads of 80 kg then 60 kg in one manufacturer-data map leave 60 kg as the
   completed result. Swapping map order swaps the result. No verified freshness
   field currently tells this implementation which is newer. Reproduce with
   `build_c20_packet(flags=5, weight_hundredths=...)` under two arbitrary keys,
   feed the returned events to a device, and reverse the map. On real C20/C1/P1/P2
   hardware, privately record ordering and candidate identity across two close
   weigh-ins and multiple proxies. Establish a model-specific discriminator and
   freshness rule before selecting a winner; do not assume dictionary order is
   arrival order. Repeated finals after the 30-second window can also acquire a
   new observation timestamp. The README no longer promises universal replay
   protection or infallible session identity.

2. **P2, proven timestamp limitation — cached replay on startup/reload.**
   `__init__.py:157-171` subscribes with HA's default cache replay and explicitly
   processes the last advertisement. A fresh parser has no persisted accepted
   identity. A cached final packet can therefore be assigned the current time
   in `device.py:104-113`. Reproduce by restoring an older pair, supplying the
   identical final packet as cached service information, and comparing
   `last_measurement_at` after setup. Deciding whether to ignore cache replay or
   restore packet identity requires a policy for measurements received while
   the integration was unloaded; this patch does not invent that policy.
   Treat these timestamps as integration observation times, not authenticated
   scale timestamps.

3. **P2, hardware hypothesis — P3 counter reset and same-counter payload changes.**
   `protocols/p3.py:121-129` rejects a low counter after a high one and drops
   equal-counter/equal-status changes. The four-byte comparison correctly
   handles ordinary progression, low-byte gaps and wraparound. Whether a
   battery replacement, factory reset, or firmware clock reset produces a
   backwards counter is unverified. Synthetic counter 5000 followed by 1 is
   rejected. Privately compare counters before/after a hardware reset and across
   repeated same-status notifications. Do not relax ordering solely on elapsed
   time, since that could admit stale frames or spoofed replays.

4. **P2, unresolved protocol evidence — OneByone notification framing.**
   `protocols/onebyone.py:21-22` accepts a valid 11-byte prefix even when trailing
   bytes exist. The MIT upstream expects exact-length measurement frames, but a
   newer shared-family implementation documents coalesced duplicate frames and
   history payloads. An exact-length hardening change was excluded because it
   could drop legitimate notifications. For A1/C1/P1, privately record lengths,
   checksums and repeated-frame markers, separately for live and history traffic.
   Reproduce acceptance with a synthetic frame plus trailing bytes. Only after
   identifying the variants should a parser reject padding or split coalesced
   frames. No GPL implementation was copied.

5. **P2, hardware/calibration limitation — impedance and composition.**
   C20 flags/offsets match the independent behavioral source, and MIT upstream
   supports the relevant weight/GATT layouts. That does not independently
   verify impedance accuracy, T9140 firmware variants, units under every scale
   display setting, or P3-derived composition on other models. Compare synthetic
   layout tests with private, consented device observations in kg/lb display
   modes, weight-only and barefoot sessions, and both supported profile modes.
   Preserve explicit opt-ins and per-capability support levels. P2/P2 Pro's
   opaque composition field remains unexposed. No medical accuracy is inferred
   from the algorithm's fixed-point reference vectors.

6. **P3 priority, maintenance — broaden routine CI version coverage.** The
   committed test extra pins HA 2026.8.3 via its fixture package, and Mypy checks
   14 listed modules rather than all HA-facing code. The existing 95% coverage
   gate excludes GATT, setup, config flow and sensors. This audit exercises
   those lifecycle paths and separately checks HA 2026.10.2, but does not silently
   upgrade project dependencies. A future CI matrix should install each HA
   version's own USB/Bluetooth manifest dependencies: the older `serialx==1.8.2`
   test pin cannot import HA 2026.10.2's USB integration, which requires 1.11.0.

## Checks that did not justify code changes

- HA 2026.8.3 explicitly awaits coroutine-returning `async_on_unload` hooks;
  that API usage is valid. The defect was ownership of in-flight connection work.
- The standard diagnostics allowlist excludes measurements, addresses, profiles,
  captures and precise timestamps. Raw capture is disabled by default and bounded
  by frame count. BLE identity checks reduce accidental mismatches but provide
  no cryptographic authenticity; plausible nearby spoofing remains possible.
- Body calculation bounds reject non-finite/out-of-range measurement values on
  the runtime path, enforce timezone-aware timestamps, and keep protocol ranges
  wider than algorithm ranges. A complete pair outside algorithm bounds leaves
  raw data available and calculated results unavailable. Profile changes
  recalculate from the last pair. The deterministic formulas and rounding were
  preserved; those tests establish reproducibility, not clinical validation.
- Automatic discovery rejects unsupported names and duplicate configured IDs;
  rediscovery cannot silently change an existing entry's model. Home Assistant
  owns rediscovery for recorded Bluetooth discovery keys. Sleeping devices do
  not make setup fail. GATT initiation remains model/option gated.
- Manifest/HACS paths, version/changelog consistency and translation keys agree.
  Release automation is restricted to successful Tests runs on main. No version
  bump, release, deployment, new dependency, or main change is part of this patch.

## Validation

Final commands and results below were recorded after the last code change. The standard
environment uses Python 3.14.5, HA 2026.8.3,
pytest-homeassistant-custom-component 0.13.357, Ruff 0.17.1 and Mypy 1.20.2.
The additional isolated environment uses HA 2026.10.2, fixture package 0.13.373,
and that HA release's `serialx==1.11.0` / `dbus-fast==5.0.22` requirements.

- `ruff format --check .`: all 56 Python files formatted.
- `ruff check .`: passed.
- `mypy`: passed, 14 configured source files.
- `pytest -q --timeout=30 --cov=custom_components/eufy_smart_scale_ble --cov-branch --cov-report=term-missing`: **229 passed in 7.49 seconds**; 13 existing config-flow warnings from pytest-socket blocking a connection with host `None`. Overall branch-inclusive coverage **94.75%** (the default report rounds this to 95%).
- `coverage report --include='*/body_composition.py,*/composition_manager.py,*/bluetooth.py,*/device.py,*/protocols/*.py' --precision=2 --fail-under=95`: **98.30%**, passed the existing CI gate.
- Separate HA 2026.10.2 `pytest -q --timeout=30 -o cache_dir=/tmp/eufy-audit-current-pytest-cache`: **229 passed in 6.64 seconds**, no warnings.
- Python compilation, JSON parsing, EN/DE translation-key equality,
  version/changelog consistency and `git diff --check`: passed.

The original 201 tests passed. New session reproductions failed before the fix
(four failures); GATT lifecycle/privacy reproductions independently failed before
the fix (five failures). A second adversarial diff review added the concurrent
timeout/unload cleanup test. Tests cannot establish radio delivery, proxy
firmware behavior, physical disconnect completion, or biometric calibration.
Local sandbox socket restrictions prevented asyncio fixture execution until the
test commands were allowed outside that sandbox; the tests still mock Bluetooth
and block external network sockets. HACS/hassfest are separate GitHub workflows,
not claimed as local passes.

## Evidence sources

- [Home Assistant Bluetooth APIs and connectability/availability guidance](https://contributors.home-assistant.io/core/integrations/bluetooth/), consulted 2026-10-22; behavior also checked in installed HA source.
- [HA 2026.8.3 config-entry lifecycle](https://github.com/home-assistant/core/blob/2026.8.3/homeassistant/config_entries.py), especially `async_on_unload`, `_async_process_on_unload` and `async_create_task`.
- [HA 2026.8.3 storage](https://github.com/home-assistant/core/blob/2026.8.3/homeassistant/helpers/storage.py) and [file permissions](https://github.com/home-assistant/core/blob/2026.8.3/homeassistant/util/file.py), checked against installed source.
- [MIT upstream client at 8916e444](https://github.com/bdr99/eufylife-ble-client/blob/8916e444c6ddb46082db184790571e7f978d36d1/eufylife_ble_client/client.py): model names, GATT characteristics, packet sizes, weight scaling and final markers.
- [openScale C20 behavior](https://github.com/oliexdev/openScale/blob/master/android_app/app/src/main/java/com/health/openscale/core/bluetooth/scales/EufyC20Handler.kt) and [OneByone behavioral caveats](https://github.com/oliexdev/openScale/blob/master/android_app/app/src/main/java/com/health/openscale/core/bluetooth/scales/OneByoneHandler.kt), consulted 2026-10-22 for protocol cross-checks only; implementation not copied.
