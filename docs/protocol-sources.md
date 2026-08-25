# Protocol sources and clean-room policy

This project implements Eufy BLE protocol behavior from public protocol facts and compatible upstream sources. It does not require vendor cloud access.

## Primary sources

| Source | License / role | Used for |
|---|---|---|
| Home Assistant Core `eufylife_ble` | Apache-2.0 upstream integration | Supported model IDs, Home Assistant behavior, integration baseline |
| `bdr99/eufylife-ble-client` | MIT | Primary compatible implementation reference for discovery, advertisements, GATT profiles, weight/final state, P2 authentication behavior |
| `cbondurant/eufy-protocol-reversal` | MIT | T9140 state/impedance protocol evidence |

## Behavioral cross-checks only

The following GPL projects are useful for independent confirmation and real-hardware reports, but their implementation code is **not copied** into this MIT repository:

- `oliexdev/openScale` — protocol/behavior cross-checks, including C20 and Onebyone-family handling.
- `KristianP26/ble-scale-sync` — protocol-family cross-checks and P2/P2 Pro real-hardware evidence.

## Per-model protocol summary

### T9150 — P3

Project hardware verification plus existing public upstream behavior. Advertisement processing uses sequence/status progression, final weight, heart-rate flag, and impedance fields.

### T9130 — C20

Home Assistant's upstream client establishes advertisement-based live/final weight. Independent public protocol evidence documents advertisement flags and offsets for impedance and heart rate.

### T9120 / T9146 / T9147 — A1 / C1 / P1

Public compatible implementations document the `FFF0` GATT family (`FFF1` write, `FFF4` notify, `2A19` battery) and `CF` measurement frames. C1/P1 additionally expose a checksum-protected embedded `CF` frame in advertisements for passive weight.

### T9140 — original Smart Scale

The upstream client documents multiple compatible notify/write characteristic families. MIT reverse-engineering work documents dynamic/final weight status bytes and impedance-process events. Because firmware variants exist, impedance remains experimental.

### T9148 / T9149 — P2 / P2 Pro

The upstream client documents passive advertisement weight, P2 Pro heart rate, and the authenticated `FFF1`/`FFF2`/`FFF4` GATT flow. A separate real-hardware report demonstrates that the commonly guessed 24-bit composition field must not be treated as a resistance value, so this project keeps it opaque.

## Fixture policy

All committed test packets are built synthetically from documented layouts. Raw BLE captures, real Bluetooth addresses, personal profiles, and real measurement values must not be committed to this repository, release notes, issues, or pull requests.
