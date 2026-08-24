"""Builders for synthetic BLE protocol fixtures.

Only documented protocol layouts and intentionally chosen synthetic values belong
in this module. Never copy real advertisement or notification captures here.
"""

from __future__ import annotations


def build_p3_packet(
    *,
    sequence: int,
    status: int,
    weight_hundredths: int,
    impedance_tenths: int = 0,
    heart_rate: int | None = None,
) -> bytes:
    """Build a protocol-shaped synthetic T9150 manufacturer payload."""
    data = bytearray(23)
    data[6] = sequence & 0xFF
    data[10] = status & 0xFF
    data[12:14] = (weight_hundredths & 0xFFFF).to_bytes(2, "little")
    if impedance_tenths:
        data[17:19] = (impedance_tenths & 0xFFFF).to_bytes(2, "little")
    if heart_rate is not None:
        data[11] |= 0x80
        data[15] = heart_rate & 0xFF
    return bytes(data)
