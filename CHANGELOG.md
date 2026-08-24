# Changelog

All notable changes to this project are documented in this file.

The project follows semantic versioning. HACS versions are published as GitHub Releases using `v<version>` tags.

## [0.2.3] - 2026-08-24

### Changed

- Refreshed public regression fixtures and test vectors with synthetic protocol data.
- No runtime integration behavior changed from `0.2.2`.

## [0.2.2] - 2026-08-24

### Fixed

- Removed an accidental development marker file from the public repository and release payload.

### Changed

- No integration behavior or body-composition calculations changed from `0.2.1`.

## [0.2.1] - 2026-08-24

### Changed

- Refined the local body-composition fixed-point reconstruction using additional validation data.
- Changed the internal weight conversion to truncate to Eufy's 0.1 kg fixed-point input instead of rounding it.
- Truncated the water base value at the fixed-point boundary before applying Eufy's water coefficient.
- Preserved fractional BMR intermediates and truncated only the displayed final value.
- Calibrated the protein estimate coefficient for closer EufyLife alignment.
- Bumped the calculation identifier to `eufy_p3_compatible_v2` so Home Assistant entity attributes show which calculation revision produced a value.

### Added

- Expanded regression coverage for the reconstructed EufyLife calculation behavior.
- Added this changelog and automated GitHub Release publishing after successful CI on `main`.
- Added CI validation to keep `manifest.json`, `pyproject.toml`, and the changelog version synchronized.

## [0.2.0] - 2026-08-24

### Added

- Added editable body-composition profile options for sex, height, age, and Normal/Athlete mode.
- Added same-session pairing of completed weight and impedance.
- Added 14 locally calculated body-composition entities: BMI, body fat, body fat mass, lean body mass, muscle mass, bone mass, body water, BMR, visceral fat, protein, skeletal muscle mass, subcutaneous fat, body age, and body type.
- Added local persistence of the latest complete weight/impedance measurement and recalculation after profile changes or Home Assistant restarts.
- Added English and German UI translations for the profile and calculated entities.

### Changed

- Refined water, skeletal muscle, and BMR display rounding.

## [0.1.0] - 2026-08-24

### Added

- Initial Home Assistant custom integration for the Eufy Smart Scale P3 (`T9150`).
- Local BLE advertisement parsing through Home Assistant Bluetooth adapters and ESPHome Bluetooth proxies.
- Reliable final-weight handling when stale and current manufacturer-data packets arrive together.
- Weight, real-time weight, impedance, heart rate, last measurement, and packet-status entities.
- HACS-compatible repository layout, automatic Bluetooth discovery, restoration, translations, tests, and CI.
