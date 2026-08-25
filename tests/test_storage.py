"""Tests for persisted complete body measurements."""

from __future__ import annotations

from datetime import UTC, datetime
from math import inf, nan

import pytest

from custom_components.eufy_smart_scale_ble.body_composition import BodyMeasurement
from custom_components.eufy_smart_scale_ble.storage import (
    deserialize_measurement,
    serialize_measurement,
)

MEASUREMENT = BodyMeasurement(
    weight_kg=78.45,
    impedance_ohm=510.0,
    measured_at=datetime(2026, 8, 24, 8, 30, 15, tzinfo=UTC),
)


def test_measurement_round_trip() -> None:
    stored = serialize_measurement(MEASUREMENT)

    assert stored == {
        "weight_kg": 78.45,
        "impedance_ohm": 510.0,
        "measured_at": "2026-08-24T08:30:15+00:00",
    }
    assert deserialize_measurement(stored) == MEASUREMENT


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"weight_kg": 78.45},
        {
            "weight_kg": "78.45",
            "impedance_ohm": 510.0,
            "measured_at": "2026-08-24T08:30:15+00:00",
        },
        {
            "weight_kg": 78.45,
            "impedance_ohm": 510.0,
            "measured_at": "not-a-date",
        },
        {
            "weight_kg": 78.45,
            "impedance_ohm": 510.0,
            "measured_at": "2026-08-24T08:30:15",
        },
    ],
)
def test_invalid_stored_shape_is_ignored(value: object) -> None:
    assert deserialize_measurement(value) is None


@pytest.mark.parametrize("weight", [nan, inf, -inf, 0.0, 200.01])
def test_invalid_weight_is_ignored(weight: float) -> None:
    value = serialize_measurement(MEASUREMENT) | {"weight_kg": weight}
    assert deserialize_measurement(value) is None


@pytest.mark.parametrize("impedance", [nan, inf, -inf, 49.9, 2000.1])
def test_invalid_impedance_is_ignored(impedance: float) -> None:
    value = serialize_measurement(MEASUREMENT) | {"impedance_ohm": impedance}
    assert deserialize_measurement(value) is None


def test_serialize_requires_timezone_aware_timestamp() -> None:
    measurement = BodyMeasurement(
        weight_kg=78.45,
        impedance_ohm=510.0,
        measured_at=datetime(2026, 8, 24, 8, 30),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        serialize_measurement(measurement)
