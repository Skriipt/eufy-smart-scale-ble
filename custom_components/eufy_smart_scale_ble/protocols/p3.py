"""Eufy Smart Scale P3 (T9150) advertisement protocol."""

from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum

from .base import (
    MeasurementEvent,
    MeasurementPhase,
    valid_heart_rate,
    valid_impedance,
    valid_weight,
)


class P3Status(IntEnum):
    LIVE = 0x01
    LOCKED = 0x05
    POST_LOCK = 0x15
    IMPEDANCE = 0x25
    BODY_COMPOSITION = 0x65
    BODY_COMPOSITION_LATE = 0xA5
    COMPLETE = 0xE5

    @property
    def slug(self) -> str:
        return {
            self.LIVE: "live",
            self.LOCKED: "locked",
            self.POST_LOCK: "post_lock",
            self.IMPEDANCE: "impedance",
            self.BODY_COMPOSITION: "body_composition",
            self.BODY_COMPOSITION_LATE: "body_composition_late",
            self.COMPLETE: "complete",
        }[self]

    @property
    def phase(self) -> MeasurementPhase:
        if self is self.LIVE:
            return MeasurementPhase.LIVE
        if self is self.LOCKED:
            return MeasurementPhase.LOCKED
        if self is self.COMPLETE:
            return MeasurementPhase.COMPLETE
        return MeasurementPhase.IMPEDANCE

    @property
    def rank(self) -> int:
        return tuple(P3Status).index(self)


def is_sequence_newer(candidate: int, reference: int) -> bool:
    delta = (candidate - reference) & 0xFF
    return 0 < delta < 128


def parse_p3_packet(raw: object) -> tuple[P3Status, MeasurementEvent] | None:
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return None
    data = bytes(raw)
    if len(data) < 19:
        return None
    try:
        status = P3Status(data[10])
    except ValueError:
        return None
    weight = int.from_bytes(data[12:14], "little") / 100
    if not valid_weight(weight):
        return None
    heart_rate = data[15] if data[11] & 0x80 else None
    if heart_rate is not None and not valid_heart_rate(heart_rate):
        heart_rate = None
    impedance = None
    if status.value & 0x20:
        candidate = int.from_bytes(data[17:19], "little") / 10
        if valid_impedance(candidate):
            impedance = candidate
    return status, MeasurementEvent(
        phase=status.phase,
        weight_kg=weight,
        impedance_ohm=impedance,
        heart_rate_bpm=heart_rate,
        sequence=data[6],
        status=status.slug,
    )


class P3AdvertisementParser:
    """Select only newer P3 packets while preserving status progression."""

    def __init__(self) -> None:
        self._sequence: int | None = None
        self._status: P3Status | None = None

    def parse(
        self, manufacturer_data: Mapping[int, object]
    ) -> tuple[MeasurementEvent, ...]:
        selected: tuple[P3Status, MeasurementEvent] | None = None
        for raw in manufacturer_data.values():
            parsed = parse_p3_packet(raw)
            if parsed is None:
                continue
            status, event = parsed
            if selected is None:
                selected = parsed
                continue
            current_status, current = selected
            assert event.sequence is not None and current.sequence is not None
            if is_sequence_newer(event.sequence, current.sequence) or (
                event.sequence == current.sequence and status.rank > current_status.rank
            ):
                selected = parsed
        if selected is None:
            return ()
        status, event = selected
        assert event.sequence is not None
        if self._sequence is not None:
            if is_sequence_newer(event.sequence, self._sequence):
                pass
            elif (
                event.sequence == self._sequence
                and self._status is not None
                and status.rank > self._status.rank
            ):
                pass
            else:
                return ()
        self._sequence = event.sequence
        self._status = status
        return (event,)
