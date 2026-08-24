# Eufy Smart Scale P3 BLE for Home Assistant

[![Tests](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant 2026.8+](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local, cloud-free Home Assistant custom integration for the **Eufy Smart Scale P3** with Bluetooth name **`eufy T9150`**.

The integration reads Bluetooth Low Energy advertisements through Home Assistant's Bluetooth stack. It works with a local Bluetooth adapter or ESPHome Bluetooth proxies and does not require an Eufy account, cloud access, or an active GATT connection to the scale.

> [!NOTE]
> This project currently supports only the Eufy Smart Scale P3 (`T9150`). It is an independent community project and is not affiliated with Eufy or Anker Innovations.

## Why this integration exists

Some Bluetooth proxies expose more than one manufacturer-data payload in one advertisement. An older live payload may therefore appear next to a newer completed measurement. Selecting only the first payload can leave the final weight unchanged.

This integration parses every valid T9150 payload, compares the scale's 8-bit sequence counters, handles counter wraparound, and selects the newest measurement phase. Duplicate, stale, malformed, and out-of-order packets are ignored safely.

Version 0.2 adds optional, fully local body-composition estimates. The scale directly transmits weight, impedance, and heart rate. When a personal profile is configured, Home Assistant combines the completed weight and impedance from the same weighing session with that profile to estimate the additional values shown below.

## Features

- Fully local BLE advertisement processing
- Automatic Bluetooth discovery
- Support for ESPHome Bluetooth proxies
- Reliable completed-weight detection
- Same-session pairing of weight and impedance
- Optional local body-composition profile
- 14 locally calculated body-composition entities
- Restored raw measurement and recalculation after restart
- No Eufy credentials, API, or cloud connection

## Entities

### Directly received from the scale

| Entity | Description |
|---|---|
| **Weight** | Most recent completed weight measurement |
| **Real-time weight** | Live weight while a measurement is in progress |
| **Impedance** | Raw bioelectrical impedance in ohms |
| **Heart rate** | Heart rate transmitted by the final measurement packets |
| **Last measurement** | Timestamp when the latest weighing session became final |
| **Packet status** | Diagnostic phase, status code, sequence number, and raw packet |

### Locally calculated

| Entity | Unit |
|---|---:|
| **BMI** | — |
| **Body fat** | % |
| **Body fat mass** | kg |
| **Lean body mass** | kg |
| **Muscle mass** | kg |
| **Bone mass** | kg |
| **Body water** | % |
| **Basal metabolic rate** | kcal/day |
| **Visceral fat** | level |
| **Protein** | % |
| **Skeletal muscle mass** | kg |
| **Subcutaneous fat** | % |
| **Body age** | years |
| **Body type** | category |

Every calculated entity includes attributes identifying the algorithm, its experimental status, the weight and impedance used, the measurement timestamp, and the profile inputs.

> [!WARNING]
> Body-composition values from consumer bioimpedance scales are estimates, not direct measurements or medical data. The local algorithm is an experimental Eufy-P3-compatible reconstruction. Small differences from the EufyLife app can occur, and the protein estimate is currently the least validated output.

## Requirements

- Home Assistant **2026.8.0 or newer**
- Home Assistant's Bluetooth integration configured and working
- A local Bluetooth adapter or ESPHome Bluetooth proxy within range
- Eufy Smart Scale P3 advertising as `eufy T9150`

## Installation

### HACS

1. Open **HACS → Integrations**.
2. Open the menu in the top-right corner and select **Custom repositories**.
3. Add:

   ```text
   https://github.com/Skriipt/eufy-smart-scale-ble
   ```

4. Select **Integration** as the category.
5. Open **Eufy Smart Scale P3 BLE** in HACS and select **Download**.
6. Restart Home Assistant.

### Manual installation

Copy `custom_components/eufy_p3_ble` to:

```text
/config/custom_components/eufy_p3_ble
```

The final path must contain the manifest directly:

```text
/config/custom_components/eufy_p3_ble/manifest.json
```

Restart Home Assistant after copying the files.

## Initial setup

1. Wake the scale by stepping on it briefly.
2. Open **Settings → Devices & services**.
3. Confirm the discovered **Eufy Smart Scale P3 BLE** integration.

You can also select **Add integration**, search for **Eufy Smart Scale P3 BLE**, and choose a currently discovered scale. No YAML configuration is required.

## Configure body-composition calculations

1. Open **Settings → Devices & services**.
2. Find **Eufy Smart Scale P3 BLE**.
3. Select **Configure**.
4. Enter the same profile values used in EufyLife:
   - sex used for calculation;
   - height in centimetres;
   - age;
   - Normal or Athlete profile mode.
5. Submit the form.

The last complete raw measurement is stored locally in Home Assistant. Changing the profile reloads the integration and immediately recalculates that measurement; another weigh-in is not required.

Calculated entities remain unavailable until both a valid profile and a complete weight-plus-impedance measurement are present.

The current release supports **one calculation profile per configured scale**. If several people use the same scale, the raw entities remain correct, but the calculated entities always use the one profile configured for this integration entry.

## Measurement behavior

A new set of calculated values is published only after weight and impedance have both arrived within the same weighing session. A weight-only reading never combines a new weight with an impedance retained from an older session.

Until a new complete body-composition measurement arrives, the previous completed values remain visible. This avoids replacing useful data with partial readings.

## Avoiding duplicate devices

Home Assistant's official **EufyLife** integration may also discover the same T9150 scale. Remove or ignore its entry for this Bluetooth address before configuring this custom integration, otherwise Home Assistant may create duplicate devices and sensors.

This integration uses its own domain, `eufy_p3_ble`, and does not replace or modify Home Assistant Core files.

## Troubleshooting

Check the following first:

- A Bluetooth adapter or proxy is within range of the scale.
- The scale appears in Home Assistant's Bluetooth diagnostics while awake.
- The official EufyLife entry for the same Bluetooth address has been removed or ignored.
- Home Assistant is running version 2026.8.0 or newer.
- `manifest.json` is directly inside `/config/custom_components/eufy_p3_ble/`.
- Body-composition profile options have been saved.
- Bare feet remain on all electrodes until the scale completes its analysis.

### Debug logging

Add temporarily to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.eufy_p3_ble: debug
```

Restart Home Assistant and perform a complete measurement. The **Packet status** entity also exposes the last accepted raw packet as a diagnostic attribute.

## Privacy

- No cloud connection
- No Eufy account or credentials
- No Eufy API access
- Profile data is stored only in the Home Assistant config entry
- The latest complete weight/impedance pair is stored only in Home Assistant's local storage
- All parsing and calculations run locally

## Development

```bash
python -m pip install -e '.[test]'
ruff format --check .
ruff check .
mypy
pytest --cov=custom_components/eufy_p3_ble --cov-branch
```

The test suite covers packet ordering, session boundaries, persistence serialization, profile parsing, body-composition reference vectors, Home Assistant options, runtime setup, and sensor behavior.

## License

Distributed under the [MIT License](LICENSE).
