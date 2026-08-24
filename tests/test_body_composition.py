"""Tests for local Eufy-compatible body composition calculations."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.eufy_p3_ble.body_composition import (
    BodyCompositionProfile,
    BodyMeasurement,
    BodyType,
    ProfileMode,
    Sex,
    calculate_body_composition,
)

MEASURED_AT = datetime(2026, 8, 24, 8, 0, tzinfo=UTC)


def test_male_reference_vector() -> None:
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=173, age=37),
        BodyMeasurement(weight_kg=72.2, impedance_ohm=433.0, measured_at=MEASURED_AT),
    )

    assert result.bmi == 24.1
    assert result.body_fat_percent == 21.4
    assert result.body_fat_mass_kg == 15.4
    assert result.lean_body_mass_kg == 56.8
    assert result.bone_mass_kg == 2.8
    assert result.muscle_mass_kg == 54.0
    assert result.body_water_percent == 53.9
    assert result.protein_percent == 14.5
    assert result.skeletal_muscle_mass_kg == 29.6
    assert result.subcutaneous_fat_percent == 18.7
    assert result.bmr_kcal_per_day == 1497
    assert result.visceral_fat_level == 11
    assert result.body_age_years == 38
    assert result.body_type is BodyType.AVERAGE


def test_female_reference_vector() -> None:
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.FEMALE, height_cm=165, age=29),
        BodyMeasurement(weight_kg=60.0, impedance_ohm=507.5, measured_at=MEASURED_AT),
    )

    assert result.bmi == 22.0
    assert result.body_fat_percent == 28.2
    assert result.body_fat_mass_kg == 16.9
    assert result.muscle_mass_kg == 40.7
    assert result.body_water_percent == 49.2
    assert result.bmr_kcal_per_day == 1232
    assert result.visceral_fat_level == 4
    assert result.body_type is BodyType.STANDARD_MUSCULAR


def test_athlete_mode_uses_adjusted_branch() -> None:
    normal = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=180, age=25),
        BodyMeasurement(weight_kg=80.0, impedance_ohm=390.0, measured_at=MEASURED_AT),
    )
    athlete = calculate_body_composition(
        BodyCompositionProfile(
            sex=Sex.MALE,
            height_cm=180,
            age=25,
            mode=ProfileMode.ATHLETE,
        ),
        BodyMeasurement(weight_kg=80.0, impedance_ohm=390.0, measured_at=MEASURED_AT),
    )

    assert athlete.body_fat_percent == 15.9
    assert athlete.bone_mass_kg == 3.4
    assert athlete.skeletal_muscle_mass_kg == 35.7
    assert athlete.bmr_kcal_per_day == 1841
    assert athlete.body_fat_percent < normal.body_fat_percent
    assert athlete.bmr_kcal_per_day > normal.bmr_kcal_per_day


def test_supplied_eufy_measurement_is_reproduced_with_calibrated_impedance() -> None:
    result = calculate_body_composition(
        BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=28),
        BodyMeasurement(weight_kg=85.3, impedance_ohm=482.0, measured_at=MEASURED_AT),
    )

    assert result.bmi == 27.8
    assert result.body_fat_percent == 27.7
    assert result.body_fat_mass_kg == 23.6
    assert result.lean_body_mass_kg == 61.7
    assert result.muscle_mass_kg == 58.6
    assert result.bone_mass_kg == 3.1
    assert result.body_water_percent == 49.6
    assert result.visceral_fat_level == 11
    assert result.skeletal_muscle_mass_kg == 32.4
    assert result.subcutaneous_fat_percent == 24.5
    assert result.body_age_years == 30
    assert result.body_type is BodyType.OBESE


@pytest.mark.parametrize(
    "profile",
    [
        BodyCompositionProfile(sex=Sex.MALE, height_cm=89, age=28),
        BodyCompositionProfile(sex=Sex.MALE, height_cm=221, age=28),
        BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=5),
        BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=100),
    ],
)
def test_rejects_invalid_profile(profile: BodyCompositionProfile) -> None:
    with pytest.raises(ValueError):
        calculate_body_composition(
            profile,
            BodyMeasurement(
                weight_kg=85.3,
                impedance_ohm=482.0,
                measured_at=MEASURED_AT,
            ),
        )


@pytest.mark.parametrize(
    ("weight", "impedance"),
    [(9.9, 482.0), (200.1, 482.0), (85.3, 199.9), (85.3, 1200.1)],
)
def test_rejects_inputs_outside_validated_ranges(
    weight: float, impedance: float
) -> None:
    with pytest.raises(ValueError):
        calculate_body_composition(
            BodyCompositionProfile(sex=Sex.MALE, height_cm=175, age=28),
            BodyMeasurement(
                weight_kg=weight,
                impedance_ohm=impedance,
                measured_at=MEASURED_AT,
            ),
        )


def test_profile_from_mapping_requires_all_profile_fields() -> None:
    from custom_components.eufy_p3_ble.body_composition import profile_from_mapping

    assert profile_from_mapping({}) is None
    assert profile_from_mapping({"sex": "male", "height_cm": 175, "age": 28}) is None


def test_profile_from_mapping_parses_home_assistant_options() -> None:
    from custom_components.eufy_p3_ble.body_composition import (
        ProfileMode,
        Sex,
        profile_from_mapping,
    )

    profile = profile_from_mapping(
        {
            "sex": "male",
            "height_cm": 175,
            "age": 28,
            "profile_mode": "athlete",
        }
    )

    assert profile == BodyCompositionProfile(
        sex=Sex.MALE,
        height_cm=175,
        age=28,
        mode=ProfileMode.ATHLETE,
    )


@pytest.mark.parametrize(
    "options",
    [
        {"sex": "unknown", "height_cm": 175, "age": 28, "profile_mode": "normal"},
        {"sex": "male", "height_cm": 89, "age": 28, "profile_mode": "normal"},
        {"sex": "male", "height_cm": 175, "age": 100, "profile_mode": "normal"},
        {"sex": "male", "height_cm": 175, "age": 28, "profile_mode": "other"},
        {"sex": "male", "height_cm": True, "age": 28, "profile_mode": "normal"},
    ],
)
def test_profile_from_mapping_rejects_invalid_options(
    options: dict[str, object],
) -> None:
    from custom_components.eufy_p3_ble.body_composition import profile_from_mapping

    assert profile_from_mapping(options) is None
