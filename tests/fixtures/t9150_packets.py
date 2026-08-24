"""Synthetic Eufy T9150 advertisement fixtures."""

from __future__ import annotations

from .builders import build_p3_packet


def make_packet(
    *,
    sequence: int,
    status: int,
    weight_kg: float = 72.35,
    heart_rate: int | None = None,
    impedance_ohm: float | None = None,
) -> bytes:
    """Build a protocol-shaped synthetic T9150 manufacturer payload."""
    packet_status = status | (0x20 if impedance_ohm is not None else 0)
    return build_p3_packet(
        sequence=sequence,
        status=packet_status,
        weight_hundredths=round(weight_kg * 100),
        impedance_tenths=(
            round(impedance_ohm * 10) if impedance_ohm is not None else 0
        ),
        heart_rate=heart_rate,
    )


LIVE_SAMPLE = make_packet(sequence=0x57, status=0x01, weight_kg=72.31)
FINAL_SAMPLE = make_packet(sequence=0x58, status=0x05, weight_kg=72.35)
IMPEDANCE_SAMPLE = make_packet(
    sequence=0x5C, status=0x25, weight_kg=72.35, impedance_ohm=510.0
)
HEART_RATE_SAMPLE = make_packet(
    sequence=0x61,
    status=0xE5,
    weight_kg=72.35,
    heart_rate=72,
    impedance_ohm=510.0,
)
