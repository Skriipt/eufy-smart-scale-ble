"""Regression tests for P3-specific display rounding behavior."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.eufy_p3_ble.body_composition import (
    BodyCompositionProfile,
    BodyMeasurement,
    Sex,
    calculate_body_composition,
)


def test_synthetic_p3_vector_keeps_fixed_point_rounding_stable() -> None:
    """Keep the reconstructed fixed-point display behavior stable."""
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=180, age=35),
        BodyMeasurement(
            weight_kg=78.45,
            impedance_ohm=510.0,
            measured_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
        ),
    )

    assert result.body_water_percent == 52.9
    assert result.skeletal_muscle_mass_kg == 31.7
    assert result.bmr_kcal_per_day == 1602
