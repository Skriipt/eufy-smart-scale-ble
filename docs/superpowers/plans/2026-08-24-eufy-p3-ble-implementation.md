# Eufy Smart Scale P3 BLE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an installable, private Home Assistant custom integration that reliably decodes Eufy Smart Scale P3 (T9150) BLE advertisements, including the stale-packet ESPHome proxy regression.

**Architecture:** A pure Python protocol layer parses and ranks advertisement frames. A small stateful device object merges weighing phases into one session. Home Assistant setup, discovery, and sensor entities consume that tested core without interpreting raw bytes.

**Tech Stack:** Python 3.14, Home Assistant 2026.8, pytest, pytest-homeassistant-custom-component, Ruff, mypy, GitHub Actions, HACS custom repository layout.

**Spec:** `docs/superpowers/specs/2026-08-24-eufy-p3-ble-design.md`

## Global Constraints

- Home Assistant `2026.8.0` or newer.
- Python `3.14.2` or newer.
- Integration domain `eufy_p3_ble`.
- T9150/P3 only in version `0.1.0`.
- Local BLE advertisements only; no cloud, credentials, network calls, or active GATT connection.
- No runtime decoder dependency.
- Do not calculate unvalidated body-composition metrics.
- Keep the official `eufylife_ble` integration untouched.

---

### Task 1: Pure T9150 frame parser

**Files:**
- Create: `custom_components/eufy_p3_ble/models.py`
- Create: `custom_components/eufy_p3_ble/parser.py`
- Create: `tests/fixtures/t9150_packets.py`
- Create: `tests/test_parser.py`

**Interfaces:**
- Produces: `PacketStatus`, `ScaleFrame`, `parse_frame(raw)`, `is_sequence_newer(candidate, reference)`.

- [x] Write parser tests for valid live/final/post-final frames, limits, malformed data, ancillary values, and wraparound.
- [x] Run the parser tests and confirm failure because parser APIs do not exist.
- [x] Implement the minimum parser and immutable frame model.
- [x] Run the parser tests and confirm all parser tests pass.

### Task 2: Newest advertisement selection

**Files:**
- Create: `custom_components/eufy_p3_ble/bluetooth.py`
- Create: `tests/test_bluetooth.py`

**Interfaces:**
- Consumes: `parse_frame`, `ScaleFrame`, sequence comparison.
- Produces: `select_newest_frame(manufacturer_data)`.

- [x] Write the stale `0x01` plus newer `0x05` regression test and ordering/deduplication tests.
- [x] Run the test file and confirm failure.
- [x] Implement all-entry parsing, raw deduplication, sequence ranking, and equal-sequence status ranking.
- [x] Run the test file and confirm pass.

### Task 3: Measurement session state machine

**Files:**
- Create: `custom_components/eufy_p3_ble/device.py`
- Create: `tests/test_device.py`

**Interfaces:**
- Consumes: `select_newest_frame`, `ScaleFrame`.
- Produces: `ScaleState`, `EufyP3Device.process()`, `EufyP3Device.register_callback()`.

- [x] Write tests for live/final separation, session timestamping, ancillary merge, stale rejection, callbacks, and new-session behavior.
- [x] Run the test file and confirm failure.
- [x] Implement the device state machine with an injected UTC clock.
- [x] Run the test file and confirm pass.

### Task 4: Home Assistant discovery and runtime setup

**Files:**
- Create: `custom_components/eufy_p3_ble/const.py`
- Create: `custom_components/eufy_p3_ble/manifest.json`
- Create: `custom_components/eufy_p3_ble/config_flow.py`
- Create: `custom_components/eufy_p3_ble/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config_flow.py`
- Create: `tests/test_init.py`

**Interfaces:**
- Produces: address-based config entries and `EufyP3RuntimeData` in `entry.runtime_data`.

- [x] Write discovery, duplicate, manual picker, setup-without-scale, initial cached packet, and unload tests.
- [x] Implement config flow and Bluetooth callback registration using Home Assistant 2026.8 APIs.
- [x] Run the Home Assistant tests under Python 3.14.

### Task 5: Six Home Assistant sensor entities

**Files:**
- Create: `custom_components/eufy_p3_ble/sensor.py`
- Create: `custom_components/eufy_p3_ble/strings.json`
- Create: `custom_components/eufy_p3_ble/translations/en.json`
- Create: `custom_components/eufy_p3_ble/translations/de.json`
- Create: `tests/test_sensor.py`

**Interfaces:**
- Consumes: `EufyP3RuntimeData.device.state` and device callbacks.
- Produces: weight, real-time weight, impedance, heart rate, last measurement, and packet status entities.

- [x] Write tests for entity creation, updates, diagnostic attributes, availability, and restore behavior.
- [x] Implement the six entities with stable unique IDs and shared Bluetooth device info.
- [x] Run sensor tests under Home Assistant 2026.8.

### Task 6: Packaging, documentation, and CI

**Files:**
- Create: `README.md`
- Create: `hacs.json`
- Create: `pyproject.toml`
- Create: `.github/workflows/tests.yml`
- Create: `.gitignore`
- Create: `LICENSE`

**Interfaces:**
- Produces: HACS/manual installation package and reproducible checks.

- [x] Document installation, migration from official EufyLife entry, sensors, privacy, and troubleshooting.
- [x] Configure Ruff, mypy, pytest, coverage, and GitHub Actions on Python 3.14.
- [x] Run Ruff lint and formatting checks.
- [x] Run mypy on the pure protocol layer.
- [x] Run the full test suite with coverage.
- [ ] Open a PR against `main` and inspect GitHub Actions.
