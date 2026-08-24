"""Local body-composition estimates for Eufy Smart Scale P3 measurements.

The scale directly provides weight and bioelectrical impedance. The remaining
values in this module are estimates produced from those inputs and a user
profile. They are not medical measurements.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import trunc
from typing import Final

ALGORITHM_ID: Final = "eufy_p3_compatible_v2"
ALGORITHM_STATUS: Final = "experimental"

MIN_HEIGHT_CM: Final = 90
MAX_HEIGHT_CM: Final = 220
MIN_AGE: Final = 6
MAX_AGE: Final = 99
MIN_WEIGHT_KG: Final = 10.0
MAX_WEIGHT_KG: Final = 200.0
MIN_IMPEDANCE_OHM: Final = 200.0
MAX_IMPEDANCE_OHM: Final = 1200.0


class Sex(StrEnum):
    """Sex branch used by the estimation algorithm."""

    MALE = "male"
    FEMALE = "female"


class ProfileMode(StrEnum):
    """Body-composition profile mode."""

    NORMAL = "normal"
    ATHLETE = "athlete"


class BodyType(StrEnum):
    """Stable Eufy-style body-type states."""

    HIDDEN_OBESE = "hidden_obese"
    UNDER_EXERCISED = "under_exercised"
    THIN = "thin"
    OBESE = "obese"
    AVERAGE = "average"
    THIN_AND_MUSCULAR = "thin_and_muscular"
    MUSCULAR_OVERWEIGHT = "muscular_overweight"
    STANDARD_MUSCULAR = "standard_muscular"
    VERY_MUSCULAR = "very_muscular"


@dataclass(frozen=True, slots=True)
class BodyCompositionProfile:
    """Personal inputs used to estimate body composition."""

    sex: Sex
    height_cm: int
    age: int
    mode: ProfileMode = ProfileMode.NORMAL


def profile_from_mapping(
    options: Mapping[str, object],
) -> BodyCompositionProfile | None:
    """Parse validated Home Assistant config-entry options into a profile."""
    sex_raw = options.get("sex")
    height_raw = options.get("height_cm")
    age_raw = options.get("age")
    mode_raw = options.get("profile_mode")
    if (
        not isinstance(sex_raw, str)
        or not isinstance(height_raw, int)
        or isinstance(height_raw, bool)
        or not isinstance(age_raw, int)
        or isinstance(age_raw, bool)
        or not isinstance(mode_raw, str)
        or not MIN_HEIGHT_CM <= height_raw <= MAX_HEIGHT_CM
        or not MIN_AGE <= age_raw <= MAX_AGE
    ):
        return None

    try:
        sex = Sex(sex_raw)
        mode = ProfileMode(mode_raw)
    except ValueError:
        return None

    return BodyCompositionProfile(
        sex=sex,
        height_cm=height_raw,
        age=age_raw,
        mode=mode,
    )


@dataclass(frozen=True, slots=True)
class BodyMeasurement:
    """One complete same-session scale measurement."""

    weight_kg: float
    impedance_ohm: float
    measured_at: datetime


@dataclass(frozen=True, slots=True)
class BodyCompositionResult:
    """Locally estimated body-composition values."""

    bmi: float
    body_fat_percent: float
    body_fat_mass_kg: float
    lean_body_mass_kg: float
    muscle_mass_kg: float
    bone_mass_kg: float
    body_water_percent: float
    bmr_kcal_per_day: int
    visceral_fat_level: int
    protein_percent: float
    skeletal_muscle_mass_kg: float
    subcutaneous_fat_percent: float
    body_age_years: int
    body_type: BodyType


_MALE_FAT_BANDS: Final[tuple[tuple[int, int, int, int], ...]] = (
    (70, 160, 250, 300),
    (70, 160, 250, 300),
    (70, 160, 260, 300),
    (70, 160, 260, 300),
    (70, 160, 260, 300),
    (70, 160, 260, 300),
    (70, 160, 250, 300),
    (70, 160, 250, 300),
    (70, 150, 250, 290),
    (80, 150, 240, 290),
    (80, 160, 240, 280),
    (90, 160, 230, 280),
    (110, 170, 220, 270),
    (120, 180, 230, 280),
    (140, 200, 250, 300),
)
_FEMALE_FAT_BANDS: Final[tuple[tuple[int, int, int, int], ...]] = (
    (80, 160, 250, 290),
    (90, 170, 250, 300),
    (100, 180, 260, 310),
    (100, 190, 280, 320),
    (110, 200, 290, 330),
    (130, 220, 310, 350),
    (140, 230, 320, 360),
    (150, 250, 340, 380),
    (170, 260, 350, 390),
    (180, 270, 360, 400),
    (190, 280, 370, 410),
    (200, 280, 370, 410),
    (210, 280, 350, 400),
    (220, 290, 360, 410),
    (230, 300, 370, 420),
)


def _trunc(value: float) -> int:
    """Truncate toward zero, matching the fixed-point implementation."""
    return trunc(value)


def _round_half_up_positive(value: float) -> int:
    """Round a non-negative value to the nearest integer, halves upward."""
    return trunc(value + 0.5)


def _rate_to_deci_kg(weight_deci_kg: int, rate_permille: int) -> int:
    return _trunc(weight_deci_kg * rate_permille / 1000)


def _deci_kg_to_rate(mass_deci_kg: int, weight_deci_kg: int) -> int:
    if weight_deci_kg == 0:
        return 0
    return _trunc(mass_deci_kg * 1000 / weight_deci_kg)


def _validate(profile: BodyCompositionProfile, measurement: BodyMeasurement) -> None:
    errors: list[str] = []
    if not MIN_HEIGHT_CM <= profile.height_cm <= MAX_HEIGHT_CM:
        errors.append(f"height_cm must be {MIN_HEIGHT_CM}..{MAX_HEIGHT_CM}")
    if not MIN_AGE <= profile.age <= MAX_AGE:
        errors.append(f"age must be {MIN_AGE}..{MAX_AGE}")
    if not MIN_WEIGHT_KG <= measurement.weight_kg <= MAX_WEIGHT_KG:
        errors.append(f"weight_kg must be {MIN_WEIGHT_KG}..{MAX_WEIGHT_KG}")
    if not MIN_IMPEDANCE_OHM <= measurement.impedance_ohm <= MAX_IMPEDANCE_OHM:
        errors.append(f"impedance_ohm must be {MIN_IMPEDANCE_OHM}..{MAX_IMPEDANCE_OHM}")
    if measurement.measured_at.tzinfo is None:
        errors.append("measured_at must be timezone-aware")
    if errors:
        raise ValueError("; ".join(errors))


def _age_band_index(age: int) -> int:
    if age < 19:
        return age - 6
    if age < 40:
        return 12
    if age < 60:
        return 13
    return 14


def _fat_bands(age: int, is_male: bool) -> tuple[int, int, int, int]:
    table = _MALE_FAT_BANDS if is_male else _FEMALE_FAT_BANDS
    return table[_age_band_index(age)]


def _muscle_bands(height_cm: int, is_male: bool) -> tuple[int, int]:
    if height_cm < 160:
        return (385, 465) if is_male else (291, 347)
    if height_cm < 170:
        return (440, 524) if is_male else (329, 375)
    return (495, 594) if is_male else (365, 425)


def _classify_body_type(
    *,
    fat_rate_permille: int,
    muscle_deci_kg: int,
    age: int,
    height_cm: int,
    is_male: bool,
) -> BodyType:
    fat_low, _, _, fat_high = _fat_bands(age, is_male)
    muscle_low, muscle_high = _muscle_bands(height_cm, is_male)

    if fat_rate_permille < fat_low:
        if muscle_deci_kg < muscle_low:
            return BodyType.THIN
        if muscle_deci_kg < muscle_high:
            return BodyType.THIN_AND_MUSCULAR
        return BodyType.VERY_MUSCULAR

    if fat_rate_permille > fat_high:
        if muscle_deci_kg < muscle_low:
            return BodyType.HIDDEN_OBESE
        if muscle_deci_kg < muscle_high:
            return BodyType.OBESE
        return BodyType.MUSCULAR_OVERWEIGHT

    if muscle_deci_kg < muscle_low:
        return BodyType.UNDER_EXERCISED
    if muscle_deci_kg < muscle_high:
        return BodyType.AVERAGE
    return BodyType.STANDARD_MUSCULAR


def calculate_body_composition(
    profile: BodyCompositionProfile,
    measurement: BodyMeasurement,
) -> BodyCompositionResult:
    """Estimate body composition from a complete P3 measurement and profile."""
    _validate(profile, measurement)

    is_male = profile.sex is Sex.MALE
    is_athlete = profile.mode is ProfileMode.ATHLETE
    height_cm = profile.height_cm
    age = profile.age
    weight_deci_kg = _trunc(measurement.weight_kg * 10)
    impedance_ohm = measurement.impedance_ohm
    height_m_squared = (height_cm / 100) ** 2

    bmi_tenths = _trunc(weight_deci_kg / height_m_squared)

    raw_fat_free_mass = (
        height_m_squared * 9.058
        + 12.226
        + weight_deci_kg * 0.032
        - impedance_ohm * 0.0068
        - age * 0.0542
    )

    adjusted_fat_free_mass = raw_fat_free_mass - (
        0.8 if is_male else (9.25 if age < 50 else 7.25)
    )
    if is_male:
        if weight_deci_kg < 0x262:
            adjusted_fat_free_mass *= 0.98
    else:
        if weight_deci_kg < 500:
            adjusted_fat_free_mass *= 1.02
        if weight_deci_kg > 600:
            adjusted_fat_free_mass *= 0.96
        if height_cm > 160:
            adjusted_fat_free_mass *= 1.03

    fat_mass_kg = weight_deci_kg / 10 - adjusted_fat_free_mass
    if is_athlete:
        fat_mass_kg = (
            fat_mass_kg * 0.778 - 0.93 if is_male else fat_mass_kg * 0.992 - 1.5
        )

    fat_rate_permille = _trunc(
        max(50.0, min(750.0, fat_mass_kg * 10000 / weight_deci_kg))
    )
    body_fat_deci_kg = _rate_to_deci_kg(weight_deci_kg, fat_rate_permille)
    lean_body_mass_deci_kg = weight_deci_kg - body_fat_deci_kg
    lean_body_mass_display_deci_kg = _round_half_up_positive(
        measurement.weight_kg * 10 - body_fat_deci_kg
    )

    bone_constant = 1.802 if is_male else 2.4569
    bone_deci_kg = _trunc(raw_fat_free_mass * 0.5158 - bone_constant)
    bone_deci_kg += -1 if bone_deci_kg < 23 else 1
    if is_athlete:
        bone_deci_kg += 1 if bone_deci_kg < 20 else 2 if bone_deci_kg < 30 else 3

    muscle_deci_kg = lean_body_mass_deci_kg - bone_deci_kg

    water_base_permille = _trunc((1000 - fat_rate_permille) * 7 / 10)
    water_rate = water_base_permille * (1.02 if water_base_permille < 501 else 0.98)
    if is_athlete:
        water_rate = water_rate * (0.996 if is_male else 0.985) + 4
    water_rate_permille = max(350, _trunc(water_rate))

    water_deci_kg = _rate_to_deci_kg(weight_deci_kg, water_rate_permille)
    skeletal_muscle_deci_kg = _trunc(water_deci_kg * 0.832 - 27.354)

    protein_deci_kg = _round_half_up_positive(water_deci_kg * 0.3133)
    protein_rate_permille = _deci_kg_to_rate(
        _trunc(protein_deci_kg - 1.36), weight_deci_kg
    )
    protein_rate_permille = max(20, min(300, protein_rate_permille))

    waist_term = impedance_ohm * 0.031 + bmi_tenths * 0.94 + age * 1.049 - 210.772
    waist_term = max(10.0, min(300.0, waist_term))
    subcutaneous_deci_kg = body_fat_deci_kg - waist_term * 9.4 / 34
    if is_athlete:
        subcutaneous_deci_kg *= 0.85
    subcutaneous_rate_permille = _trunc(subcutaneous_deci_kg * 1000 / weight_deci_kg)
    subcutaneous_rate_permille = max(10, min(600, subcutaneous_rate_permille))

    if is_male:
        bmr_raw = weight_deci_kg * 1.4916 + 877.8 - height_cm * 0.726 - age * 8.976
    else:
        bmr_raw = weight_deci_kg * 1.02036 + 864.6 - height_cm * 0.39336 - age * 6.204
    if is_athlete:
        bmr_raw = bmr_raw * 1.16 - 149
    bmr = max(500, _trunc(bmr_raw))

    height_squared = height_cm * height_cm
    if is_male:
        if height_cm < weight_deci_kg * 0.16 + 63:
            visceral_fat = (
                weight_deci_kg * 30.5 / (height_squared * 0.0826 - height_cm * 0.4 + 48)
                - 2.9
                + age * 0.15
            )
        else:
            visceral_fat = (
                (-0.0015 * height_cm + 0.765) * weight_deci_kg / 10
                - height_cm * 0.143
                + age * 0.15
                - 5
            )
    elif height_cm * 5 - 130 < weight_deci_kg:
        visceral_fat = (
            weight_deci_kg * 50 / (height_squared * 0.1158 + height_cm * 1.45 - 120)
            - 6
            + age * 0.07
        )
    else:
        visceral_fat = (
            (-0.0024 * height_cm + 0.691) * weight_deci_kg / 10
            - height_cm * 0.027
            + age * 0.07
            - 10.5
        )

    if is_athlete:
        if visceral_fat < 2:
            visceral_fat = 1
        elif visceral_fat < 10:
            visceral_fat -= 2
        elif visceral_fat < 20:
            visceral_fat *= 0.8
        else:
            visceral_fat *= 0.85
    visceral_fat_level = 1 if visceral_fat < 1 else min(50, _trunc(visceral_fat))

    body_age_first = _trunc(age + 28.428 - bmi_tenths * 0.1428)
    body_age_first = max(age - 5, min(age + 5, body_age_first))
    body_age_second = _trunc(age + bmi_tenths * 0.1724 - 34.931)
    body_age_second = max(age - 8, min(age + 8, body_age_second))
    body_age = _trunc(body_age_first * 0.4 + body_age_second * 0.6)
    body_age = max(MIN_AGE, min(MAX_AGE, body_age))

    body_type = _classify_body_type(
        fat_rate_permille=fat_rate_permille,
        muscle_deci_kg=muscle_deci_kg,
        age=age,
        height_cm=height_cm,
        is_male=is_male,
    )

    return BodyCompositionResult(
        bmi=bmi_tenths / 10,
        body_fat_percent=fat_rate_permille / 10,
        body_fat_mass_kg=body_fat_deci_kg / 10,
        lean_body_mass_kg=lean_body_mass_display_deci_kg / 10,
        muscle_mass_kg=muscle_deci_kg / 10,
        bone_mass_kg=bone_deci_kg / 10,
        body_water_percent=water_rate_permille / 10,
        bmr_kcal_per_day=bmr,
        visceral_fat_level=visceral_fat_level,
        protein_percent=protein_rate_permille / 10,
        skeletal_muscle_mass_kg=skeletal_muscle_deci_kg / 10,
        subcutaneous_fat_percent=subcutaneous_rate_permille / 10,
        body_age_years=body_age,
        body_type=body_type,
    )
