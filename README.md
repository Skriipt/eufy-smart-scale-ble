# Eufy Smart Scale BLE for Home Assistant

[![Tests](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant 2026.8+](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Use a compatible Eufy smart scale in Home Assistant with local Bluetooth Low Energy (BLE)—no Eufy account, cloud API, or vendor credentials required. The integration receives the measurements the scale provides and can optionally calculate local body-composition estimates when reliable impedance is available.

> [!IMPORTANT]
> **Compatibility:** Home Assistant **2026.8.0 or newer** with a working Bluetooth adapter or compatible ESPHome Bluetooth proxy is required. The integration supports the eight Eufy models in the [support matrix](docs/support-matrix.md), but only the P3/T9150 has been verified with this project's hardware. Other support is capability-specific and marked as upstream validated or experimental.
>
> **Not included:** EufyLife/cloud synchronization, a cloud API, or a guarantee that every metric is available on every supported model. Body-composition estimates are not medical measurements.

This is an independent community project and is not affiliated with Eufy or Anker Innovations.

## Quick start

1. Install the integration through HACS and restart Home Assistant.
2. Wake the scale by stepping on it briefly.
3. In **Settings → Devices & services**, confirm the discovered **Eufy Smart Scale BLE** integration.
4. Complete a weigh-in.

A completed weigh-in updates the measurements supported by your model. Body-composition entities stay unavailable until the model supplies a reliable same-session impedance reading and its required profile/options are configured.

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

### Upgrading from 0.2.x

Version 0.3.0 changed the integration domain from `eufy_p3_ble` to `eufy_smart_scale_ble`. Home Assistant config-entry domains cannot be safely rewritten in place, so early installations need a one-time re-add:

1. Remove the existing **Eufy Smart Scale P3 BLE** config entry.
2. Update or reinstall through HACS, or replace the manual integration files.
3. Remove a stale `/config/custom_components/eufy_p3_ble` directory if it remains.
4. Restart Home Assistant, add **Eufy Smart Scale BLE** again, and re-enter profile options if used.

Entity registry entries may be recreated because the integration domain changed.

## Set up and measure

### Add the scale

Wake the scale, then open **Settings → Devices & services** and confirm the discovered integration. You can also select **Add integration**, search for **Eufy Smart Scale BLE**, and choose a currently discovered supported scale. No YAML configuration is required.

If Home Assistant's official **EufyLife** integration discovers the same Bluetooth device, remove or ignore that entry before adding this integration to avoid duplicate devices and sensors.

### Choose model-specific options

Options are shown only where they apply:

| Model | What is available |
|---|---|
| **P3 / T9150** | Body-composition profile is available by default. |
| **C20 / T9130** and **A1 / T9120** | Experimental cross-model body composition can be explicitly enabled. A1 uses GATT. |
| **C1 / T9146** and **P1 / T9147** | Passive weight works without a connection. Enable **Extended metrics** to allow short GATT sessions for impedance/battery, then optionally enable experimental cross-model composition. |
| **T9140** | Experimental impedance and composition are off by default because characteristic/firmware variants differ. |
| **P2 / T9148** and **P2 Pro / T9149** | Weight is supported; impedance and body composition are not offered. |

For body-composition calculations, enter the profile fields shown by the integration. The latest legitimate complete weight-and-impedance measurement is stored locally so profile changes can recalculate without another weigh-in.

### What to expect from a weigh-in

- **Weight-only measurement:** completed weight is updated; it never reuses impedance from an earlier session.
- **Complete body-composition measurement:** final weight and impedance from the same active session are paired, then calculated values are updated.
- **Partial measurement:** previous calculated values remain visible rather than being replaced by incomplete data.

For an impedance measurement, stay barefoot on all electrodes until the scale finishes its analysis.

## What the integration exposes

Entities are created only when the configured model can provide the underlying capability.

| Group | Possible entities |
|---|---|
| **Measurements** | Weight, real-time weight, impedance, heart rate, battery, and last measurement |
| **Diagnostics** | Packet status, with privacy-safe parser/session information |
| **Local estimates** | BMI; body fat percentage and mass; lean, muscle, bone, and skeletal muscle mass; body water; basal metabolic rate; visceral fat; protein; subcutaneous fat; body age; and body type |

Body-composition estimates require a reliable final weight and impedance pair from one session. The local algorithm is experimental and is calibrated primarily against the P3/T9150; cross-model calculations require explicit opt-in where available.

> [!WARNING]
> Consumer bioimpedance values are estimates, not direct measurements or medical data. The integration intentionally does not expose the ambiguous P2/P2 Pro composition field as impedance or use it for body-composition calculations.

## Supported models and reliable BLE handling

See the [full support matrix](docs/support-matrix.md) for each model's transport and capability level, and [protocol sources](docs/protocol-sources.md) for the evidence behind upstream-validated support.

Where a model broadcasts enough data, the integration processes passive BLE advertisements through Home Assistant's Bluetooth stack. It opens short-lived GATT connections only for models or optional metrics that need them. For each measurement, it applies model-specific protocol handling and session safety so that duplicate, stale, malformed, or out-of-order packets do not overwrite a newer completed result.

## Privacy, diagnostics, and limitations

- No cloud connection, Eufy account, credentials, or Eufy API access is used.
- All parsing and calculations run locally in Home Assistant.
- Profile data is stored only in the Home Assistant config entry. The latest complete measurement is stored locally to support restoration and recalculation after restart.
- Standard Home Assistant diagnostics exclude Bluetooth addresses, raw packets, measurements, profile fields, and precise measurement timestamps. They contain only safe technical metadata.
- Advanced protocol capture is off by default, bounded in memory only, cleared on reload/restart, and never included in normal diagnostics. Raw BLE data can encode personal measurements—do not upload it publicly without careful review.

See [Model verification](docs/model-verification.md) if you can help verify hardware that is not yet tested by this project.

## Troubleshooting

| Symptom | What to check |
|---|---|
| The scale is not discovered | Wake it, confirm it is one of the [supported models](docs/support-matrix.md), and ensure a Home Assistant Bluetooth adapter or proxy is in range. Check Home Assistant's Bluetooth diagnostics while the scale is awake. |
| No scale is available when adding manually | Wake it and try **Add integration** again; the manual flow lists only currently discovered supported scales. |
| Raw values update but body-composition entities are unavailable | Confirm the model supports reliable impedance, configure the profile/options, and complete a barefoot measurement that includes impedance. |
| Calculated values appear old | This is expected after a partial or weight-only measurement. Values update only after a new final weight-and-impedance pair from the same session. |
| C1/P1 has no impedance or battery | Enable **Extended metrics** to allow the needed short-lived GATT connection. |
| Duplicate devices or sensors appear | Remove or ignore the official EufyLife integration entry for the same Bluetooth device. |
| The integration does not load | Confirm Home Assistant is 2026.8.0 or newer and that `manifest.json` is directly at `/config/custom_components/eufy_smart_scale_ble/manifest.json`. |

### Debug logging

Temporarily add:

```yaml
logger:
  logs:
    custom_components.eufy_smart_scale_ble: debug
```

Restart Home Assistant and perform a measurement. Prefer the integration's privacy-safe diagnostics when opening a public issue.

## Releases and contributing

See the [changelog](CHANGELOG.md) for release notes. Issues and contributions are welcome through this repository.

For local development:

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
