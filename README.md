# Eufy Smart Scale BLE for Home Assistant

[![Tests](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant 2026.8+](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Bring compatible Eufy smart-scale measurements into Home Assistant over local
Bluetooth Low Energy (BLE). No Eufy account, cloud API, or vendor credentials
are required.

The integration supports eight Eufy scale models with capability-specific
coverage. The P3/T9150 is tested with project-owned hardware; support for the
other models is based on compatible public protocol implementations and is
clearly marked below.

> [!IMPORTANT]
> Home Assistant **2026.8.0 or newer** and a working Bluetooth adapter or
> compatible ESPHome Bluetooth proxy are required. Available entities depend on
> the scale model. Body-composition values are experimental estimates, not
> medical measurements.

This independent community project is not affiliated with Eufy or Anker
Innovations.

## Quick start

1. Install the integration through HACS and restart Home Assistant.
2. Wake the scale by stepping on it briefly.
3. Open **Settings → Devices & services** and confirm the discovered
   **Eufy Smart Scale BLE** integration.
4. Complete a weigh-in.

No YAML configuration is required. If discovery does not appear, select
**Add integration**, search for **Eufy Smart Scale BLE**, and choose a currently
discovered scale.

If Home Assistant's official **EufyLife** integration also discovers the same
scale, remove or ignore that entry to avoid duplicate devices and sensors.

## Installation

### HACS

This repository is not yet part of the HACS default store. Add it as a custom
repository:

1. Open **HACS → Integrations**.
2. Open the top-right menu and select **Custom repositories**.
3. Enter `https://github.com/Skriipt/eufy-smart-scale-ble`.
4. Select **Integration** as the category and add the repository.
5. Open **Eufy Smart Scale BLE** and select **Download**.
6. Restart Home Assistant.

### Manual installation

Copy the entire `custom_components/eufy_smart_scale_ble` directory into your
Home Assistant configuration directory so that this file exists:

```text
/config/custom_components/eufy_smart_scale_ble/manifest.json
```

Restart Home Assistant after copying or replacing the files.

### Upgrading from 0.2.x

Version 0.3.0 changed the integration domain from `eufy_p3_ble` to
`eufy_smart_scale_ble`. Home Assistant cannot safely rewrite an existing config
entry to a new domain, so upgrading requires a one-time re-add:

1. Remove the existing **Eufy Smart Scale P3 BLE** config entry.
2. Update through HACS or replace the files from a manual installation.
3. Delete the old `/config/custom_components/eufy_p3_ble` directory if it is
   still present.
4. Restart Home Assistant and add **Eufy Smart Scale BLE** again.
5. Re-enter any body-composition profile options you used previously.

Entity registry entries may be recreated because the integration domain
changed.

## Measurements and options

### During a weigh-in

The integration separates live readings from completed measurements and never
combines values from different sessions:

- A weight-only session updates the completed weight without reusing older
  impedance.
- A complete session pairs final weight and impedance only when both belong to
  the same weigh-in, then updates the calculated body-composition values.
- A partial session leaves the previous calculated values in place rather than
  replacing them with incomplete data.

For impedance, stand barefoot on all electrodes until the scale finishes its
analysis.

### Body composition

The local calculation can provide BMI, body fat percentage and mass, lean body
mass, muscle mass, bone mass, body water, basal metabolic rate, visceral fat,
protein, skeletal muscle mass, subcutaneous fat, body age, and body type.

These entities require a model with usable impedance, a completed same-session
weight-and-impedance pair, and the profile fields shown in the integration
options. The latest valid pair is stored locally so changing the profile can
recalculate the values without another weigh-in.

The calculation is calibrated primarily against the P3/T9150 and remains
experimental. It is enabled by default only for that model. On supported
cross-model paths, it must be enabled explicitly in the integration options.

> [!WARNING]
> Consumer bioimpedance values are estimates. Do not use them for diagnosis or
> medical decisions. The P2/P2 Pro composition field is intentionally not
> exposed as impedance because available evidence does not support that
> interpretation.

### Model-specific options

- **C1/T9146 and P1/T9147:** enable **Extended metrics** to allow short GATT
  connections for impedance and battery. Experimental body composition also
  requires this option.
- **Original Smart Scale/T9140:** experimental impedance and experimental body
  composition are separate opt-ins because firmware and characteristic variants
  exist.
- **A1/T9120 and C20/T9130:** experimental cross-model body composition is
  available as an explicit opt-in.
- **P2/T9148 and P2 Pro/T9149:** impedance and body composition are unavailable.

## Compatibility

Support is tracked per capability: support for weight does not imply support for
impedance or body composition.

- **Verified** means tested with real hardware by this project.
- **Upstream validated** means implemented from reputable compatible public
  projects, but not yet tested with project-owned hardware.
- **Experimental** means available only with explicit caution or an opt-in.
- **Unsupported** means the protocol evidence is not reliable enough to expose
  the capability.

| Model | Weight | Other available measurements | Body composition | BLE transport |
|---|---|---|---|---|
| A1 / T9120 | Upstream validated | Impedance, battery | Experimental opt-in | GATT |
| C20 / T9130 | Upstream validated | Impedance, heart rate | Experimental opt-in | Advertisements |
| Smart Scale / T9140 | Upstream validated | Battery; experimental impedance, off by default | Experimental, off by default | GATT |
| C1 / T9146 | Upstream validated | Impedance and battery with **Extended metrics** | Experimental opt-in | Advertisements + optional GATT |
| P1 / T9147 | Upstream validated | Impedance and battery with **Extended metrics** | Experimental opt-in | Advertisements + optional GATT |
| P2 / T9148 | Upstream validated | None | Unsupported | Advertisements |
| P2 Pro / T9149 | Upstream validated | Heart rate | Unsupported | Advertisements |
| P3 / T9150 | **Verified** | **Verified impedance and heart rate** | Experimental, enabled by default | Advertisements |

The [full support matrix](docs/support-matrix.md) contains detailed capability
notes. [Protocol sources](docs/protocol-sources.md) documents the public evidence
behind non-P3 support.

## Entities

Home Assistant creates entities only when the configured model and enabled
options can provide the underlying capability.

- **Measurements:** completed weight, real-time weight, impedance, heart rate,
  battery, and last measurement.
- **Status:** packet status with parser and measurement-session information.
- **Local estimates:** the body-composition values listed above.

Not every entity appears for every scale. The compatibility table describes the
capability boundaries; it is not an assurance that a scale emits every value on
every weigh-in.

## Bluetooth behavior

Models that advertise sufficient data are handled passively through Home
Assistant's Bluetooth stack. The integration opens short-lived GATT connections
only for models or optional metrics that require them.

Model-specific parsing and session handling prevent duplicate, stale, malformed,
or out-of-order packets from overwriting a newer completed result.

## Privacy and diagnostics

- Parsing and body-composition calculations run locally in Home Assistant.
- The integration does not connect to Eufy's cloud or request an Eufy account,
  credentials, or API access.
- Profile data remains in the Home Assistant config entry. The latest complete
  weight-and-impedance pair is stored in Home Assistant storage for restoration
  and local recalculation.
- Standard Home Assistant diagnostics exclude Bluetooth addresses, raw packets,
  measurements, profile fields, and precise measurement timestamps. They contain
  only model, protocol, capability, parser/session, and connection metadata.
- Advanced protocol capture is disabled by default, limited to 100 frames in
  memory, cleared on reload or restart, and excluded from standard diagnostics.

Raw BLE data can encode personal measurements. Do not post protocol captures,
Bluetooth addresses, measurements, profile data, or screenshots containing
personal values in public issues. Prefer the integration's standard diagnostics.

See [Model verification](docs/model-verification.md) for the privacy-safe process
for testing hardware that has not yet been verified by this project.

## Troubleshooting

**The scale is not discovered**

Wake the scale, keep it near a Home Assistant Bluetooth adapter or proxy, and
confirm that its discovery name appears in the [support matrix](docs/support-matrix.md).
Check Home Assistant's Bluetooth diagnostics while the scale is awake.

**No scale is available when adding the integration manually**

The manual flow lists only supported scales that are currently discovered. Wake
the scale and try **Add integration** again.

**Weight updates, but body-composition entities are unavailable**

Confirm that the model supports impedance, enable the required experimental or
extended options, complete the profile, and perform a barefoot measurement that
reaches a final impedance reading.

**Calculated values did not change after a weigh-in**

This is expected after a partial or weight-only session. Calculated values update
only after a new final weight-and-impedance pair from the same session.

**C1/P1 does not show impedance or battery**

Enable **Extended metrics** in the integration options. This permits the required
short-lived GATT connection.

**Duplicate devices or sensors appear**

Remove or ignore the official EufyLife integration entry for the same scale.

**The integration does not load**

Confirm that Home Assistant is 2026.8.0 or newer and that `manifest.json` is
located directly at
`/config/custom_components/eufy_smart_scale_ble/manifest.json`.

### Debug logging

Temporarily add this to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.eufy_smart_scale_ble: debug
```

Restart Home Assistant, reproduce the problem, and review the log. Remove the
debug configuration afterwards to avoid unnecessary log volume. When opening a
public issue, attach privacy-safe diagnostics and review every attachment for
personal data first.

## Releases and contributing

See the [changelog](CHANGELOG.md) for release notes. Bug reports and hardware
verification are welcome through the [issue tracker](https://github.com/Skriipt/eufy-smart-scale-ble/issues).

For local development:

```bash
python -m pip install -e '.[test]'
ruff format --check .
ruff check .
mypy
pytest --cov=custom_components/eufy_smart_scale_ble --cov-branch
```

All committed BLE fixtures must be synthetic. Never commit raw captures,
Bluetooth addresses, or personal measurement/profile data.

## License

Distributed under the [MIT License](LICENSE).
