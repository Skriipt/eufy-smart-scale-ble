"""Sanitized Eufy T9150 advertisement fixtures."""

from __future__ import annotations


def make_packet(
    *,
    sequence: int,
    status: int,
    weight_kg: float = 82.75,
    heart_rate: int | None = None,
    impedance_ohm: float | None = None,
) -> bytes:
    """Build a protocol-shaped sanitized T9150 manufacturer payload."""
    data = bytearray.fromhex("e80712209d0000d6f96100000000010000000000000000")
    data[6] = sequence & 0xFF
    data[10] = status & 0xFF
    weight_raw = round(weight_kg * 100)
    data[12] = weight_raw & 0xFF
    data[13] = (weight_raw >> 8) & 0xFF
    if heart_rate is not None:
        data[11] |= 0x80
        data[15] = heart_rate & 0xFF
    if impedance_ohm is not None:
        data[10] |= 0x20
        impedance_raw = round(impedance_ohm * 10)
        data[17] = impedance_raw & 0xFF
        data[18] = (impedance_raw >> 8) & 0xFF
    return bytes(data)


LIVE_82_71 = make_packet(sequence=0x57, status=0x01, weight_kg=82.71)
FINAL_82_75 = make_packet(sequence=0x58, status=0x05, weight_kg=82.75)
IMPEDANCE_82_75 = make_packet(
    sequence=0x5C, status=0x25, weight_kg=82.75, impedance_ohm=435.0
)
HEART_RATE_82_75 = make_packet(
    sequence=0x61,
    status=0xE5,
    weight_kg=82.75,
    heart_rate=72,
    impedance_ohm=435.0,
)
