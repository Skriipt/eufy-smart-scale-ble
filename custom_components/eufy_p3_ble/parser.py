"""Parser for Eufy Smart Scale P3 (T9150) BLE advertisements."""

from __future__ import annotations

from typing import Final

from .models import PacketStatus, ScaleFrame

MIN_PACKET_LENGTH: Final = 19
MIN_WEIGHT_KG: Final = 0.0
MAX_WEIGHT_KG: Final = 200.0
MIN_HEART_RATE_BPM: Final = 30
MAX_HEART_RATE_BPM: Final = 240
MIN_IMPEDANCE_OHM: Final = 50.0
MAX_IMPEDANCE_OHM: Final = 2000.0


def is_sequence_newer(candidate: int, reference: int) -> bool:
    """Return whether an unsigned 8-bit counter is newer than another."""
    delta = (candidate - reference) & 0xFF
    return 0 < delta < 128


def parse_frame(raw: object) -> ScaleFrame | None:
    """Validate and decode one T9150 manufacturer-data payload.

    Malformed or unsupported input is intentionally ignored. Bluetooth
    advertisements are untrusted, lossy input and must never break the HA callback.
    """
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return None

    data = bytes(raw)
    if len(data) < MIN_PACKET_LENGTH:
        return None

    try:
        status = PacketStatus(data[10])
    except ValueError:
        return None

    weight_kg = int.from_bytes(data[12:14], byteorder="little") / 100
    if not MIN_WEIGHT_KG < weight_kg <= MAX_WEIGHT_KG:
        return None

    heart_rate_bpm: int | None = None
    if data[11] & 0x80:
        candidate_heart_rate = data[15]
        if MIN_HEART_RATE_BPM <= candidate_heart_rate <= MAX_HEART_RATE_BPM:
            heart_rate_bpm = candidate_heart_rate

    impedance_ohm: float | None = None
    if status.value & 0x20:
        candidate_impedance = int.from_bytes(data[17:19], byteorder="little") / 10
        if MIN_IMPEDANCE_OHM <= candidate_impedance <= MAX_IMPEDANCE_OHM:
            impedance_ohm = candidate_impedance

    return ScaleFrame(
        raw=data,
        sequence=data[6],
        status=status,
        weight_kg=weight_kg,
        heart_rate_bpm=heart_rate_bpm,
        impedance_ohm=impedance_ohm,
    )
