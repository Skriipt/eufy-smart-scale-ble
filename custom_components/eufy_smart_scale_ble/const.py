"""Constants for Eufy Smart Scale BLE."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "eufy_smart_scale_ble"
MANUFACTURER: Final = "Eufy"

CONF_SEX: Final = "sex"
CONF_HEIGHT_CM: Final = "height_cm"
CONF_AGE: Final = "age"
CONF_PROFILE_MODE: Final = "profile_mode"
CONF_EXTENDED_METRICS: Final = "extended_metrics"
CONF_EXPERIMENTAL_COMPOSITION: Final = "experimental_cross_model_composition"
CONF_EXPERIMENTAL_IMPEDANCE: Final = "experimental_impedance"
CONF_PROTOCOL_CAPTURE: Final = "protocol_capture"

DEFAULT_SEX: Final = "male"
DEFAULT_HEIGHT_CM: Final = 175
DEFAULT_AGE: Final = 30
DEFAULT_PROFILE_MODE: Final = "normal"
