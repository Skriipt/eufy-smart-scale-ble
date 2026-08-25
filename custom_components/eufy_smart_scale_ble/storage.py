"""Persistence helpers for the latest complete body measurement."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING, Any, Final

from .body_composition import BodyMeasurement

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_STORAGE_VERSION: Final = 1
_STORAGE_KEY_PREFIX: Final = "eufy_smart_scale_ble.body_measurement"
_MIN_WEIGHT_KG: Final = 0.0
_MAX_WEIGHT_KG: Final = 200.0
_MIN_IMPEDANCE_OHM: Final = 50.0
_MAX_IMPEDANCE_OHM: Final = 2000.0


def serialize_measurement(measurement: BodyMeasurement) -> dict[str, float | str]:
    """Serialize a complete raw measurement for Home Assistant storage."""
    if measurement.measured_at.tzinfo is None:
        raise ValueError("measured_at must be timezone-aware")
    return {
        "weight_kg": measurement.weight_kg,
        "impedance_ohm": measurement.impedance_ohm,
        "measured_at": measurement.measured_at.isoformat(),
    }


def deserialize_measurement(value: object) -> BodyMeasurement | None:
    """Deserialize a stored measurement, ignoring malformed or unsafe values."""
    if not isinstance(value, dict):
        return None

    weight = value.get("weight_kg")
    impedance = value.get("impedance_ohm")
    measured_at_raw = value.get("measured_at")
    if (
        not isinstance(weight, (int, float))
        or isinstance(weight, bool)
        or not isinstance(impedance, (int, float))
        or isinstance(impedance, bool)
        or not isinstance(measured_at_raw, str)
    ):
        return None

    weight_kg = float(weight)
    impedance_ohm = float(impedance)
    if (
        not isfinite(weight_kg)
        or not _MIN_WEIGHT_KG < weight_kg <= _MAX_WEIGHT_KG
        or not isfinite(impedance_ohm)
        or not _MIN_IMPEDANCE_OHM <= impedance_ohm <= _MAX_IMPEDANCE_OHM
    ):
        return None

    try:
        measured_at = datetime.fromisoformat(measured_at_raw)
    except ValueError:
        return None
    if measured_at.tzinfo is None:
        return None

    return BodyMeasurement(
        weight_kg=weight_kg,
        impedance_ohm=impedance_ohm,
        measured_at=measured_at,
    )


def _store(hass: HomeAssistant, entry_id: str) -> Any:
    from homeassistant.helpers.storage import Store

    return Store(
        hass,
        _STORAGE_VERSION,
        f"{_STORAGE_KEY_PREFIX}.{entry_id}",
    )


async def async_load_measurement(
    hass: HomeAssistant, entry_id: str
) -> BodyMeasurement | None:
    """Load the latest complete measurement for one config entry."""
    return deserialize_measurement(await _store(hass, entry_id).async_load())


async def async_save_measurement(
    hass: HomeAssistant,
    entry_id: str,
    measurement: BodyMeasurement,
) -> None:
    """Persist the latest complete measurement for one config entry."""
    await _store(hass, entry_id).async_save(serialize_measurement(measurement))
