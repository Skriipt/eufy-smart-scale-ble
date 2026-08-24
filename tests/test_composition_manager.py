"""Tests for body-composition runtime coordination."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.eufy_p3_ble.body_composition import (
    BodyCompositionProfile,
    BodyMeasurement,
    Sex,
)
from custom_components.eufy_p3_ble.composition_manager import BodyCompositionManager

MEASUREMENT = BodyMeasurement(
    weight_kg=85.3,
    impedance_ohm=482.0,
    measured_at=datetime(2026, 8, 24, 8, 30, tzinfo=UTC),
)
PROFILE = BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=28)


def test_initial_profile_and_measurement_are_calculated() -> None:
    manager = BodyCompositionManager(profile=PROFILE, measurement=MEASUREMENT)

    assert manager.profile == PROFILE
    assert manager.measurement == MEASUREMENT
    assert manager.result is not None
    assert manager.result.body_fat_percent == 27.7


def test_measurement_is_retained_until_profile_is_configured() -> None:
    manager = BodyCompositionManager(profile=None, measurement=MEASUREMENT)

    assert manager.measurement == MEASUREMENT
    assert manager.result is None

    assert manager.update_profile(PROFILE)
    assert manager.result is not None
    assert manager.result.body_type.value == "obese"


def test_new_measurement_notifies_once_and_duplicate_is_ignored() -> None:
    manager = BodyCompositionManager(profile=PROFILE)
    results = []
    manager.register_callback(results.append)

    assert manager.update_measurement(MEASUREMENT)
    assert len(results) == 1
    assert results[0] == manager.result

    assert not manager.update_measurement(MEASUREMENT)
    assert len(results) == 1


def test_invalid_algorithm_input_remains_available_as_raw_measurement() -> None:
    invalid_for_algorithm = BodyMeasurement(
        weight_kg=85.3,
        impedance_ohm=150.0,
        measured_at=MEASUREMENT.measured_at,
    )
    manager = BodyCompositionManager(profile=PROFILE)

    assert manager.update_measurement(invalid_for_algorithm)
    assert manager.measurement == invalid_for_algorithm
    assert manager.result is None


def test_callback_unsubscribe_is_idempotent() -> None:
    manager = BodyCompositionManager(profile=PROFILE)
    calls = []
    unsubscribe = manager.register_callback(calls.append)

    unsubscribe()
    unsubscribe()
    manager.update_measurement(MEASUREMENT)

    assert calls == []
