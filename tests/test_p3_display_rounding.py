"""Regression tests for P3-specific display rounding observed in EufyLife."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.eufy_p3_ble.body_composition import (
    BodyCompositionProfile,
    BodyMeasurement,
    Sex,
    calculate_body_composition,
)


def test_supplied_p3_measurement_matches_eufylife_display_rounding() -> None:
    """Keep the locally calculated values aligned with the supplied P3 result."""
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=28),
        BodyMeasurement(
            weight_kg=85.3,
            impedance_ohm=482.0,
            measured_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
        ),
    )

    assert result.body_water_percent == 49.5
    assert result.skeletal_muscle_mass_kg == 32.3
    assert result.bmr_kcal_per_day == 1771
