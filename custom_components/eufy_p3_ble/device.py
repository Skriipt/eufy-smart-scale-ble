"""Stateful measurement session handling for the Eufy P3."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime

from .bluetooth import select_newest_frame
from .models import PacketStatus, ScaleFrame, ScaleState
from .parser import is_sequence_newer

StateCallback = Callable[[ScaleState], None]
Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EufyP3Device:
    """Merge advertisement packets into stable Home Assistant values."""

    def __init__(self, *, now: Clock = _utcnow) -> None:
        self._now = now
        self._state = ScaleState()
        self._callbacks: list[StateCallback] = []
        self._session_finalized = False

    @property
    def state(self) -> ScaleState:
        """Return the immutable current state snapshot."""
        return self._state

    def register_callback(self, callback: StateCallback) -> Callable[[], None]:
        """Register a state listener and return an idempotent unsubscribe call."""
        self._callbacks.append(callback)
        removed = False

        def unsubscribe() -> None:
            nonlocal removed
            if removed:
                return
            removed = True
            with suppress(ValueError):
                self._callbacks.remove(callback)

        return unsubscribe

    def process(self, manufacturer_data: Mapping[int, object]) -> bool:
        """Process one advertisement and return whether state changed."""
        frame = select_newest_frame(manufacturer_data)
        if frame is None or not self._accept_frame(frame):
            return False

        previous = self._state
        if frame.status is PacketStatus.LIVE:
            if previous.packet_status is not PacketStatus.LIVE:
                self._session_finalized = False
            updated = replace(
                previous,
                real_time_weight_kg=frame.weight_kg,
                packet_status=frame.status,
                sequence=frame.sequence,
                raw_packet_hex=frame.raw.hex(),
            )
        else:
            timestamp = previous.last_measurement_at
            if not self._session_finalized:
                timestamp = self._now()
                self._session_finalized = True
            updated = replace(
                previous,
                real_time_weight_kg=frame.weight_kg,
                weight_kg=frame.weight_kg,
                impedance_ohm=(
                    frame.impedance_ohm
                    if frame.impedance_ohm is not None
                    else previous.impedance_ohm
                ),
                heart_rate_bpm=(
                    frame.heart_rate_bpm
                    if frame.heart_rate_bpm is not None
                    else previous.heart_rate_bpm
                ),
                last_measurement_at=timestamp,
                packet_status=frame.status,
                sequence=frame.sequence,
                raw_packet_hex=frame.raw.hex(),
            )

        if updated == previous:
            return False
        self._state = updated
        for callback in tuple(self._callbacks):
            callback(updated)
        return True

    def _accept_frame(self, frame: ScaleFrame) -> bool:
        """Reject duplicate or out-of-order callbacks across advertisements."""
        previous_sequence = self._state.sequence
        previous_status = self._state.packet_status
        if previous_sequence is None:
            return True
        if is_sequence_newer(frame.sequence, previous_sequence):
            return True
        if frame.sequence != previous_sequence or previous_status is None:
            return False
        return frame.status.rank > previous_status.rank
