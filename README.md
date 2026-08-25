# Eufy Smart Scale BLE for Home Assistant

[![Tests](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant 2026.8+](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local, cloud-free Home Assistant integration for Eufy smart scales over Bluetooth Low Energy.

The integration supports every scale model currently handled by Home Assistant's EufyLife BLE integration. It uses passive advertisements where the scale broadcasts enough data and opens a short-lived GATT connection only for models or optional capabilities that require one. No Eufy account, cloud API, or vendor credentials are required.

> [!NOTE]
> This is an independent community project and is not affiliated with Eufy or Anker Innovations. Only the P3/T9150 is hardware-verified by this project; other models are implemented from compatible upstream protocol sources and are clearly marked accordingly.

## Supported models

| Model | Weight / final | Heart rate | Impedance | Body composition | Transport |
|---|---|---|---|---|---|
| Smart Scale A1 / T9120 | Upstream Validated | — | Upstream Validated | Experimental opt-in | GATT |
| Smart Scale C20 / T9130 | Upstream Validated | Upstream Validated | Upstream Validated | Experimental opt-in | Advertisement |
| Smart Scale / T9140 | Upstream Validated | — | Experimental, off by default | Experimental, off by default | GATT |
| Smart Scale C1 / T9146 | Upstream Validated | — | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| Smart Scale P1 / T9147 | Upstream Validated | — | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| Smart Scale P2 / T9148 | Upstream Validated | — | Unsupported | Unavailable | Advertisement |
| Smart Scale P2 Pro / T9149 | Upstream Validated | Upstream Validated | Unsupported | Unavailable | Advertisement |
| Smart Scale P3 / T9150 | **Verified** | **Verified** | **Verified** | Experimental algorithm, enabled | Advertisement |

Support levels are tracked per capability, not just per model:

- **Verified** — tested with real hardware by this project.
- **Upstream Validated** — supported by reputable compatible upstream implementations, but not hardware-tested by this project.
- **Experimental** — plausible protocol evidence exists, but the capability is intentionally gated until further verification.
- **Unsupported** — the protocol is not reliable enough to expose the capability.

See [the full support matrix](docs/support-matrix.md) and [protocol sources](docs/protocol-sources.md).

## Features

- Fully local BLE processing
- Automatic Bluetooth discovery for all eight supported model IDs
- Local Bluetooth adapters and ESPHome Bluetooth proxies
- Passive advertisement processing wherever possible
- Short-lived GATT connections only when needed
- Reliable live/final-weight handling
- Same-session protection for weight and impedance
- Capability-gated entities per model
- Optional local body-composition estimates when reliable impedance is available
- Restored completed measurements and local recalculation after restart
- Privacy-safe Home Assistant diagnostics
- Explicit, memory-only advanced protocol capture option
- No Eufy credentials, API, or cloud connection

## Entities

Entities are created only when the configured model can provide the underlying capability. Depending on the scale, these may include:

- **Weight** — most recent completed weight
- **Real-time weight** — live weight during a measurement
- **Impedance** — raw impedance when reliably decoded
- **Heart rate** — when supported by the model/protocol
- **Battery** — for GATT models that expose the standard battery characteristic
- **Last measurement** — timestamp of the latest final measurement
- **Packet status** — privacy-safe diagnostic parser/session status

When body composition is enabled and the scale provides a reliable final weight plus impedance from the same measurement session, the integration can calculate:

- BMI
- body fat percentage and mass
- lean body mass
- muscle mass
- bone mass
- body water
- basal metabolic rate
- visceral fat
- protein
- skeletal muscle mass
- subcutaneous fat
- body age
- body type

> [!WARNING]
> Consumer bioimpedance values are estimates, not medical measurements. The local body-composition algorithm is an experimental reconstruction calibrated primarily against the P3/T9150. Cross-model calculations are disabled by default and must be explicitly enabled where available.

### Why P2/P2 Pro do not expose body composition

Public protocol implementations expose a 24-bit field for P2/P2 Pro, but available real-hardware evidence shows that treating it as impedance produces implausible resistance values. This integration therefore keeps that field opaque and never labels it as impedance or feeds it into body-composition formulas.

## Requirements

- Home Assistant **2026.8.0 or newer**
- Home Assistant Bluetooth configured and working
- A local Bluetooth adapter or compatible ESPHome Bluetooth proxy within range
- One of the supported Eufy scale models listed above

## Installation

### HACS

Until this repository is accepted into the HACS default store, install it as a custom repository:

1. Open **HACS → Integrations**.
2. Open the top-right menu and select **Custom repositories**.
3. Add:

   ```text
   https://github.com/Skriipt/eufy-smart-scale-ble
   ```

4. Select **Integration** as the category.
5. Open **Eufy Smart Scale BLE** and select **Download**.
6. Restart Home Assistant.

### Manual installation

Copy `custom_components/eufy_smart_scale_ble` to:

```text
/config/custom_components/eufy_smart_scale_ble
```

The manifest must then be at:

```text
/config/custom_components/eufy_smart_scale_ble/manifest.json
```

Restart Home Assistant after copying the files.

## Upgrading from 0.2.x to 0.3.0

Version 0.3.0 changes the Home Assistant integration domain from `eufy_p3_ble` to `eufy_smart_scale_ble`. Home Assistant config-entry domains cannot be safely rewritten in place, so existing early installations need a one-time re-add:

1. Remove the existing **Eufy Smart Scale P3 BLE** config entry.
2. Update/reinstall the integration through HACS or replace the manual integration files.
3. If a stale `/config/custom_components/eufy_p3_ble` directory remains, remove it.
4. Restart Home Assistant.
5. Add **Eufy Smart Scale BLE** again.
6. Re-enter body-composition profile options if used.

Entity registry entries may be recreated because the integration domain changed.

## Initial setup

1. Wake the scale by stepping on it briefly.
2. Open **Settings → Devices & services**.
3. Confirm the discovered **Eufy Smart Scale BLE** device.

You can also select **Add integration**, search for **Eufy Smart Scale BLE**, and choose a currently discovered supported scale. No YAML configuration is required.

## Options and extended metrics

Options are model-dependent:

- **P3/T9150:** body-composition profile is available by default.
- **C20/T9130:** experimental cross-model body composition can be explicitly enabled.
- **A1/T9120:** GATT is required; experimental cross-model body composition can be enabled when desired.
- **C1/T9146 and P1/T9147:** passive weight works without a connection. Enable **Extended metrics** to permit short GATT sessions for impedance/battery, then optionally enable experimental cross-model composition.
- **T9140:** experimental impedance is disabled by default because several characteristic/firmware variants exist.
- **P2/T9148 and P2 Pro/T9149:** no impedance/body-composition option is offered.
- **Protocol capture:** advanced, disabled by default, memory-only, and never included in normal diagnostics.

For body-composition calculations, configure the profile fields shown by the integration. The latest legitimate complete weight/impedance measurement is stored locally so profile changes can recalculate without another weigh-in.

## Measurement safety

A body-composition measurement is created only when final weight and impedance belong to the same active weighing session. A new weight can never silently reuse impedance from a previous measurement.

Unsupported or experimental raw fields are never converted into normal entities unless the relevant option explicitly enables an experimental path.

## Avoiding duplicate devices

Home Assistant's official **EufyLife** integration may also discover the same scale. Remove or ignore its entry for the same Bluetooth device before configuring this custom integration, otherwise Home Assistant may create duplicate devices and sensors.

## Diagnostics and privacy

Standard Home Assistant diagnostics intentionally exclude:

- Bluetooth/MAC address
- raw advertisements/notifications
- weight
- impedance
- heart rate
- age, height, sex, or profile mode
- precise measurement timestamps

They contain only safe technical metadata such as model, protocol family, transport, support levels, parser status names, packet lengths, and counters.

The optional advanced protocol-capture mode stores raw packets only in a bounded in-memory buffer. It is off by default, not persisted, cleared on reload/restart, and never added to normal diagnostics. Raw BLE data can encode personal measurements and should not be uploaded publicly without careful review.

See [Model verification](docs/model-verification.md) if you want to help verify hardware we do not own.

## Troubleshooting

Check these first:

- A Bluetooth adapter or proxy is within range.
- The scale appears in Home Assistant Bluetooth diagnostics while awake.
- The official EufyLife entry for the same device has been removed or ignored.
- Home Assistant is 2026.8.0 or newer.
- `manifest.json` is directly inside `/config/custom_components/eufy_smart_scale_ble/`.
- For C1/P1 extended metrics, the **Extended metrics** option is enabled.
- Body-composition profile/options are configured for models that support them.

### Debug logging

Temporarily add:

```yaml
logger:
  logs:
    custom_components.eufy_smart_scale_ble: debug
```

Restart Home Assistant and perform a measurement. Prefer the integration's privacy-safe diagnostics when opening a public issue.

## Development

```bash
python -m pip install -e '.[test]'
ruff format --check .
ruff check .
mypy
pytest --cov=custom_components/eufy_smart_scale_ble --cov-branch
```

All committed BLE fixtures must be synthetic. Do not commit raw captures or personal measurement/profile data.

## License

Distributed under the [MIT License](LICENSE).
