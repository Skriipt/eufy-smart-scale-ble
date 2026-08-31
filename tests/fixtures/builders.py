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
    data[6:10] = (sequence & 0xFFFFFFFF).to_bytes(4, "little")
    data[10] = status & 0xFF
    data[12:14] = (weight_hundredths & 0xFFFF).to_bytes(2, "little")
    if impedance_tenths:
        data[17:19] = (impedance_tenths & 0xFFFF).to_bytes(2, "little")
    if heart_rate is not None:
        data[11] |= 0x80
        data[15] = heart_rate & 0xFF
    return bytes(data)


def _xor(data: bytes) -> int:
    result = 0
    for value in data:
        result ^= value
    return result


def build_c20_packet(
    *,
    flags: int,
    weight_hundredths: int = 0,
    impedance_tenths: int = 0,
    heart_rate: int = 0,
) -> bytes:
    data = bytearray(23)
    data[10] = flags
    data[12:14] = weight_hundredths.to_bytes(2, "little")
    data[15] = heart_rate & 0xFF
    data[17:19] = impedance_tenths.to_bytes(2, "little")
    return bytes(data)


def build_onebyone_frame(
    *,
    weight_hundredths: int,
    impedance_tenths: int = 0,
    final: bool,
    impedance_present: bool = True,
) -> bytes:
    data = bytearray(11)
    data[0] = 0xCF
    data[1] = impedance_tenths & 0xFF
    data[2] = (impedance_tenths >> 8) & 0xFF
    data[3:5] = weight_hundredths.to_bytes(2, "little")
    data[9] = 0x00 if final else (0x03 if impedance_present else 0x01)
    data[-1] = _xor(data[:-1])
    return bytes(data)


def build_onebyone_advertisement(**kwargs) -> bytes:
    frame = build_onebyone_frame(**kwargs)
    data = bytearray(18)
    data[4:15] = frame
    return bytes(data)


def build_t9140_weight(*, weight_tenths: int, final: bool) -> bytes:
    data = bytearray(8)
    data[2:4] = weight_tenths.to_bytes(2, "big")
    data[6] = 0xCA if final else 0xCE
    return bytes(data)


def build_t9140_impedance(*, impedance_ohm: int) -> bytes:
    data = bytearray(8)
    data[2:4] = b"\xfd\x01"
    data[4:6] = impedance_ohm.to_bytes(2, "big")
    data[6] = 0xCB
    return bytes(data)


def build_p2_advertisement(
    *,
    weight_hundredths: int,
    final: bool,
    heart_rate: int | None = None,
    opaque_field: int = 0,
) -> bytes:
    data = bytearray(19)
    data[6] = 0xCF
    if heart_rate is not None:
        data[7] = heart_rate & 0xFF
        data[8] = 0xC0
    data[9:11] = weight_hundredths.to_bytes(2, "little")
    data[12:15] = opaque_field.to_bytes(3, "little")
    data[15] = 0x00 if final else 0x01
    return bytes(data)
