# Eufy Smart Scale P3 BLE for Home Assistant

[![Tests](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/Skriipt/eufy-smart-scale-ble/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant 2026.8+](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local, cloud-free Home Assistant custom integration for the **Eufy Smart Scale P3** with Bluetooth name **`eufy T9150`**.

The integration reads Bluetooth Low Energy advertisements through Home Assistant's Bluetooth stack. It works with a local Bluetooth adapter as well as ESPHome Bluetooth proxies and does not require an Eufy account, cloud access, or an active connection to the scale.

> [!NOTE]
> This project currently supports only the Eufy Smart Scale P3 (`T9150`). It is an independent community project and is not affiliated with Eufy or Anker Innovations.

## Why this integration exists

Some Bluetooth proxies may expose more than one manufacturer-data payload in the same advertisement. One payload can contain an older live reading while another already contains the completed measurement. Selecting only the first payload can therefore leave Home Assistant's final weight sensor unchanged.

This integration parses every valid T9150 payload, compares the scale's 8-bit sequence counters, handles counter wraparound, and selects the newest measurement phase. Duplicate, stale, malformed, and out-of-order packets are ignored safely.

## Features

- Fully local BLE advertisement processing
- Automatic Bluetooth discovery
- Support for ESPHome Bluetooth proxies
- Reliable completed-weight detection
- Sequence-counter wraparound handling
- Restored completed values after Home Assistant restarts
- No Eufy credentials, API, or cloud connection

## Entities

| Entity | Description |
|---|---|
| **Weight** | Most recent completed weight measurement; restored after restart |
| **Real-time weight** | Live weight while a measurement is in progress |
| **Impedance** | Raw impedance value transmitted by the scale in ohms; restored after restart |
| **Heart rate** | Heart-rate value transmitted by the scale in bpm; restored after restart |
| **Last measurement** | Timestamp when the latest measurement first became final |
| **Packet status** | Diagnostic measurement phase with status code, sequence number, and raw packet attributes |

Derived values such as body-fat percentage, muscle mass, body water, visceral fat, or BMI are intentionally not calculated. Producing trustworthy values would require additional profile data and a validated calculation model.

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

1. Copy the directory:

   ```text
   custom_components/eufy_p3_ble
   ```

   to:

   ```text
   /config/custom_components/eufy_p3_ble
   ```

2. Restart Home Assistant.

The final path must contain the manifest directly:

```text
/config/custom_components/eufy_p3_ble/manifest.json
```

## Configuration

After installation and restart:

1. Wake the scale by stepping on it briefly.
2. Open **Settings → Devices & services**.
3. Confirm the discovered **Eufy Smart Scale P3 BLE** integration.

You can also select **Add integration**, search for **Eufy Smart Scale P3 BLE**, and choose a currently discovered scale.

No YAML configuration is required.

## Avoiding duplicate devices

Home Assistant's official **EufyLife** integration may also discover the same T9150 scale. Remove or ignore the official EufyLife entry for this scale before configuring this custom integration. Otherwise, Home Assistant may create duplicate devices and sensors.

This custom integration uses its own domain, `eufy_p3_ble`, and does not replace or modify any Home Assistant Core files.

## Verifying a measurement

1. Open the **Eufy Smart Scale P3** device in Home Assistant.
2. Step on the scale and remain still until the measurement locks.
3. **Real-time weight** should update while the scale is measuring.
4. **Weight** should then retain the final locked value.
5. **Impedance** and **Heart rate** may arrive slightly later when the scale completes its body-composition phase.
6. Restart Home Assistant to confirm that completed values are restored.

## Troubleshooting

Check the following first:

- A Bluetooth adapter or proxy is within range of the scale.
- The scale appears in Home Assistant's Bluetooth diagnostics while awake.
- The official EufyLife entry for the same Bluetooth address has been removed or ignored.
- Home Assistant is running version 2026.8.0 or newer.
- The integration directory contains `manifest.json` at the expected path.

### Debug logging

Add the following temporarily to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.eufy_p3_ble: debug
```

Restart Home Assistant and perform a complete measurement. Normal logging does not expose raw packets. Packet details are available only through diagnostic entity attributes and debug-level logs.

## Privacy

- No cloud connection
- No Eufy account or credentials
- No Eufy API access
- No age, height, sex, or profile data
- All measurements are processed locally inside Home Assistant

## Development

The protocol parser and measurement-session logic are tested independently from Home Assistant. The repository also contains Home Assistant integration tests and GitHub Actions validation.

```bash
python -m pip install -e '.[test]'
ruff format --check .
ruff check .
mypy
pytest --cov=custom_components/eufy_p3_ble --cov-branch
```

## License

Distributed under the [MIT License](LICENSE).
