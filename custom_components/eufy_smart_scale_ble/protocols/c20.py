"""Eufy Smart Scale C20 (T9130) advertisement protocol."""

from __future__ import annotations

from collections.abc import Mapping

from .base import (
    MeasurementEvent,
    MeasurementPhase,
    valid_heart_rate,
    valid_impedance,
    valid_weight,
)


class C20AdvertisementParser:
    def parse(
        self, manufacturer_data: Mapping[int, object]
    ) -> tuple[MeasurementEvent, ...]:
        events: list[MeasurementEvent] = []
        for raw in manufacturer_data.values():
            if not isinstance(raw, (bytes, bytearray, memoryview)):
                continue
            data = bytes(raw)
            if len(data) < 14:
                continue
            flags = data[10]
            has_weight = bool(flags & 0x01)
            has_impedance = bool(flags & 0x40)
            has_heart_rate = bool(flags & 0x80)
            weight = int.from_bytes(data[12:14], "little") / 100 if has_weight else None
            if weight is not None and not valid_weight(weight):
                weight = None
            impedance = (
                int.from_bytes(data[17:19], "little") / 10
                if has_impedance and len(data) >= 19
                else None
            )
            if impedance is not None and not valid_impedance(impedance):
                impedance = None
            heart_rate = data[15] if has_heart_rate and len(data) >= 16 else None
            if heart_rate is not None and not valid_heart_rate(heart_rate):
                heart_rate = None
            if weight is None and impedance is None and heart_rate is None:
                continue
            final_weight = has_weight and (flags & 0x05) == 0x05
            phase = MeasurementPhase.LOCKED if final_weight else MeasurementPhase.LIVE
            if impedance is not None and weight is None:
                phase = MeasurementPhase.IMPEDANCE
            events.append(
                MeasurementEvent(
                    phase=phase,
                    weight_kg=weight,
                    impedance_ohm=impedance,
                    heart_rate_bpm=heart_rate,
                    status=f"0x{flags:02x}",
                )
            )
        return tuple(events)
