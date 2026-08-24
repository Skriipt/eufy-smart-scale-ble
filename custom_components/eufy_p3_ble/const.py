"""Constants for the Eufy Smart Scale P3 BLE integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "eufy_p3_ble"
MODEL_ID: Final = "eufy T9150"
MODEL_NAME: Final = "T9150"
DEVICE_NAME: Final = "Eufy Smart Scale P3"
MANUFACTURER: Final = "Eufy"
VERSION: Final = "0.2.6"

CONF_SEX: Final = "sex"
CONF_HEIGHT_CM: Final = "height_cm"
CONF_AGE: Final = "age"
CONF_PROFILE_MODE: Final = "profile_mode"

DEFAULT_SEX: Final = "male"
DEFAULT_HEIGHT_CM: Final = 175
DEFAULT_AGE: Final = 30
DEFAULT_PROFILE_MODE: Final = "normal"
