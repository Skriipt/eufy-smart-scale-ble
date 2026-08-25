# Changelog

All notable changes to this project are documented in this file.

The project follows semantic versioning. HACS versions are published as GitHub Releases using `v<version>` tags.

## [0.3.0] - 2026-08-25

### Added

- Added capability-driven support for all eight Eufy smart-scale model IDs currently handled by Home Assistant EufyLife BLE.
- Added protocol families for C20 advertisements, C1/P1 advertisements and optional GATT enrichment, A1 GATT measurements, legacy T9140 GATT measurements, and P2/P2 Pro advertisements.
- Added per-capability support levels: Verified, Upstream Validated, Experimental, and Unsupported.
- Added short-lived GATT transport with battery support for models that require active connections.
- Added privacy-safe Home Assistant diagnostics and an explicit memory-only advanced protocol-capture option.
- Added public support-matrix, protocol-source, and privacy-safe model-verification documentation.

### Changed

- Renamed the integration display name to `Eufy Smart Scale BLE`.
- Changed the Home Assistant integration domain from `eufy_p3_ble` to `eufy_smart_scale_ble`. Existing 0.2.x installations require a one-time remove/re-add after upgrading.
- Preserved the hardware-verified P3 behavior behind the generic protocol/session architecture.
- Body-composition entities are now capability-gated and only operate when a reliable same-session final weight and impedance pair exists.
- Cross-model body-composition calculations are experimental and disabled by default outside the P3.

### Safety

- P2/P2 Pro opaque composition bytes are not exposed as impedance and are never used for body-composition calculations.
- Standard diagnostics exclude Bluetooth addresses, raw BLE payloads, personal profile fields, and measurement values.
- Public protocol fixtures remain synthetic only.

## [0.2.7] - 2026-08-24

### Added

- Added the public GitHub issue tracker to the Home Assistant integration manifest for HACS repository validation.
- Added HACS validation with `hacs/action@main` for the `integration` category without ignored checks.
- Added Home Assistant Hassfest validation with `home-assistant/actions/hassfest@master` without bypassing failures.

### Changed

- Prepared repository metadata and CI for a future official HACS listing while keeping the current Custom Repository installation flow until acceptance.
- No runtime integration behavior or body-composition calculations changed from `0.2.6`.

## [0.2.6] - 2026-08-24

### Added

- Added Home Assistant brand assets for the integration: a 256×256 `icon.png` and a 512×512 `icon@2x.png`.
- Added an original scale-and-Bluetooth icon without vendor branding for clear display in Home Assistant and HACS.

### Changed

- No runtime integration behavior or body-composition calculations changed from `0.2.5`.

## [0.2.5] - 2026-08-24

### Privacy

- Removed non-synthetic validation data from public test fixtures and release notes.
- Public regression coverage now uses synthetic values only.

### Changed

- No runtime integration behavior or body-composition calculations changed from `0.2.4`.

## [0.2.4] - 2026-08-24

### Fixed

- Aligned Lean Body Mass display rounding with EufyLife by using the scale's full two-decimal weight for the displayed subtraction while preserving the 0.1 kg fixed-point path used by dependent calculations such as Muscle Mass.
- Rounded the final Protein percentage to the nearest 0.1% for EufyLife display parity.

### Added

- Expanded synthetic regression coverage for all calculated body-composition outputs and display-rounding behavior.

### Changed

- Bumped the local calculation identifier to `eufy_p3_compatible_v3`.

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
