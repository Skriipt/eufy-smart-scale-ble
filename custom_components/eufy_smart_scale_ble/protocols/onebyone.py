"""Shared A1/C1/P1 OneByone-family protocol."""

from __future__ import annotations

from collections.abc import Mapping

from .base import MeasurementEvent, MeasurementPhase, valid_impedance, valid_weight


def xor_checksum(data: bytes) -> int:
    checksum = 0
    for value in data:
        checksum ^= value
    return checksum


def valid_checksum(data: bytes) -> bool:
    return len(data) > 1 and xor_checksum(data[:-1]) == data[-1]


def parse_cf_frame(data: bytes, *, include_impedance: bool) -> MeasurementEvent | None:
    if len(data) < 11 or data[0] != 0xCF or not valid_checksum(data[:11]):
        return None
    weight = int.from_bytes(data[3:5], "little") / 100
    if not valid_weight(weight) or data[9] == 0x02:
        return None
    final = data[9] == 0x00
    impedance = None
    if include_impedance and data[9] != 0x01:
        candidate = ((data[2] << 8) | data[1]) * 0.1
        if valid_impedance(candidate):
            impedance = candidate
    return MeasurementEvent(
        phase=MeasurementPhase.LOCKED if final else MeasurementPhase.LIVE,
        weight_kg=weight,
        impedance_ohm=impedance,
        status="locked" if final else "live",
    )


class OnebyoneAdvertisementParser:
    def parse(
        self, manufacturer_data: Mapping[int, object]
    ) -> tuple[MeasurementEvent, ...]:
        for raw in manufacturer_data.values():
            if not isinstance(raw, (bytes, bytearray, memoryview)):
                continue
            data = bytes(raw)
            if len(data) == 18 and data[4] == 0xCF:
                event = parse_cf_frame(data[4:15], include_impedance=False)
                if event is not None:
                    return (event,)
        return ()


def parse_onebyone_gatt(data: bytes) -> MeasurementEvent | None:
    return parse_cf_frame(data, include_impedance=True)
