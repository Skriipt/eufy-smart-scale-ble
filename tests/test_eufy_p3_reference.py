"""Regression tests against a real Eufy Smart Scale P3 measurement."""

from datetime import UTC, datetime

from custom_components.eufy_p3_ble.body_composition import (
    BodyCompositionProfile,
    BodyMeasurement,
    BodyType,
    Sex,
    calculate_body_composition,
)


def test_real_p3_measurement_matches_eufylife_display() -> None:
    """Match the values displayed by EufyLife for a captured P3 measurement."""
    # EufyLife effectively used calculation age 28 for this captured measurement.
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=28),
        BodyMeasurement(
            weight_kg=85.75,
            impedance_ohm=452.4,
            measured_at=datetime(2026, 8, 24, 17, 55, 5, tzinfo=UTC),
        ),
    )

    assert result.bmi == 27.9
    assert result.body_fat_percent == 27.6
    assert result.body_fat_mass_kg == 23.6
    assert result.lean_body_mass_kg == 62.2
    assert result.muscle_mass_kg == 59.0
    assert result.bone_mass_kg == 3.1
    assert result.body_water_percent == 49.5
    assert result.bmr_kcal_per_day == 1777
    assert result.visceral_fat_level == 11
    assert result.protein_percent == 15.3
    assert result.skeletal_muscle_mass_kg == 32.5
    assert result.subcutaneous_fat_percent == 24.4
    assert result.body_age_years == 30
    assert result.body_type is BodyType.OBESE
