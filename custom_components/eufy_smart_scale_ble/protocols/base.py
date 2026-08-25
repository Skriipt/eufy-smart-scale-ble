"""Normalized protocol events shared by all supported scales."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MeasurementPhase(StrEnum):
    LIVE = "live"
    LOCKED = "locked"
    IMPEDANCE = "impedance"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class MeasurementEvent:
    phase: MeasurementPhase
    weight_kg: float | None = None
    impedance_ohm: float | None = None
    heart_rate_bpm: int | None = None
    battery_percent: int | None = None
    sequence: int | None = None
    status: str | None = None


MIN_WEIGHT_KG = 0.0
MAX_WEIGHT_KG = 200.0
MIN_IMPEDANCE_OHM = 50.0
MAX_IMPEDANCE_OHM = 2000.0
MIN_HEART_RATE_BPM = 30
MAX_HEART_RATE_BPM = 240


def valid_weight(value: float) -> bool:
    return MIN_WEIGHT_KG < value <= MAX_WEIGHT_KG


def valid_impedance(value: float) -> bool:
    return MIN_IMPEDANCE_OHM <= value <= MAX_IMPEDANCE_OHM


def valid_heart_rate(value: int) -> bool:
    return MIN_HEART_RATE_BPM <= value <= MAX_HEART_RATE_BPM
