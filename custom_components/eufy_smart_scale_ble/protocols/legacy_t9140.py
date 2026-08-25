"""Original Eufy Smart Scale (T9140) GATT protocol."""

from __future__ import annotations

from .base import MeasurementEvent, MeasurementPhase, valid_impedance, valid_weight


NOTIFY_CANDIDATES = (
    "4143f7b2-5300-4900-4700-414943415245",
    "4143f6b2-5300-4900-4700-414943415245",
    "0000ffb2-0000-1000-8000-00805f9b34fb",
)
WRITE_CANDIDATES = (
    "4143f7b1-5300-4900-4700-414943415245",
    "4143f6b1-5300-4900-4700-414943415245",
    "0000ffb1-0000-1000-8000-00805f9b34fb",
)


def split_notifications(data: bytes) -> tuple[bytes, ...]:
    if len(data) >= 2 and data[:2] == b"\xac\x02":
        if len(data) == 16:
            return (data[8:15], data[0:8])
        if len(data) == 17:
            return (data[9:16], data[0:9])
    return (data,)


def parse_t9140_frame(
    data: bytes, *, allow_impedance: bool = False
) -> MeasurementEvent | None:
    if len(data) < 7:
        return None
    if data[6] in (0xCA, 0xCE):
        weight = int.from_bytes(data[2:4], "big") / 10
        if not valid_weight(weight):
            return None
        final = data[6] == 0xCA
        return MeasurementEvent(
            phase=MeasurementPhase.LOCKED if final else MeasurementPhase.LIVE,
            weight_kg=weight,
            status="locked" if final else "live",
        )
    if allow_impedance and data[6] == 0xCB and data[2] == 0xFD and data[3] == 0x01:
        impedance = float(int.from_bytes(data[4:6], "big"))
        if valid_impedance(impedance):
            return MeasurementEvent(
                phase=MeasurementPhase.IMPEDANCE,
                impedance_ohm=impedance,
                status="impedance",
            )
    return None
