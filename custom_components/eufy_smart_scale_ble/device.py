"""Generic weighing-session state for all supported Eufy scales."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from .body_composition import BodyMeasurement
from .models import ScaleState
from .protocols.base import MeasurementEvent, MeasurementPhase

StateCallback = Callable[[ScaleState], None]
Clock = Callable[[], datetime]
_SAME_SESSION_WINDOW = timedelta(seconds=30)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EufyScaleDevice:
    def __init__(
        self,
        *,
        now: Clock = _utcnow,
        restored_measurement: BodyMeasurement | None = None,
    ) -> None:
        self._now = now
        # RestoreSensor owns the latest raw values. A persisted composition pair
        # may predate a newer weight-only measurement and must not overwrite it.
        self._state = ScaleState(body_measurement=restored_measurement)
        self._callbacks: list[StateCallback] = []
        self._session_phase: MeasurementPhase | None = None
        self._session_finalized = False
        self._session_weight: float | None = None
        self._session_impedance: float | None = None
        self._session_impedance_at: datetime | None = None
        self._session_time: datetime | None = None

    @property
    def state(self) -> ScaleState:
        return self._state

    def register_callback(self, callback: StateCallback) -> Callable[[], None]:
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

    def begin_session(self) -> None:
        self._session_phase = None
        self._session_finalized = False
        self._session_weight = None
        self._session_impedance = None
        self._session_impedance_at = None
        self._session_time = None

    def process_event(self, event: MeasurementEvent) -> bool:
        previous = self._state
        has_measurement = event.weight_kg is not None or event.impedance_ohm is not None
        if not has_measurement:
            # Battery reads and standalone heart-rate updates are not weigh-ins.
            updated = replace(
                previous,
                heart_rate_bpm=(
                    event.heart_rate_bpm
                    if event.heart_rate_bpm is not None
                    else previous.heart_rate_bpm
                ),
                battery_percent=(
                    event.battery_percent
                    if event.battery_percent is not None
                    else previous.battery_percent
                ),
            )
        elif event.phase is MeasurementPhase.LIVE:
            if self._session_phase is not MeasurementPhase.LIVE:
                self.begin_session()
            if event.impedance_ohm is not None:
                self._session_impedance = event.impedance_ohm
                self._session_impedance_at = self._now()
            updated = replace(
                previous,
                real_time_weight_kg=(
                    event.weight_kg
                    if event.weight_kg is not None
                    else previous.real_time_weight_kg
                ),
                heart_rate_bpm=(
                    event.heart_rate_bpm
                    if event.heart_rate_bpm is not None
                    else previous.heart_rate_bpm
                ),
                battery_percent=(
                    event.battery_percent
                    if event.battery_percent is not None
                    else previous.battery_percent
                ),
                packet_status=event.status or event.phase.value,
                sequence=event.sequence
                if event.sequence is not None
                else previous.sequence,
            )
        else:
            event_time = self._now()
            if self._session_time is not None and not (
                timedelta() <= event_time - self._session_time <= _SAME_SESSION_WINDOW
            ):
                self.begin_session()
            if self._should_begin_without_live(event):
                self.begin_session()
            if not self._session_finalized and event.weight_kg is not None:
                self._session_time = event_time
                self._session_finalized = True
            if event.weight_kg is not None:
                self._session_weight = event.weight_kg
            if event.impedance_ohm is not None:
                self._session_impedance = event.impedance_ohm
                self._session_impedance_at = event_time
            body_measurement = previous.body_measurement
            if (
                self._session_weight is not None
                and self._session_impedance is not None
                and self._session_impedance_at is not None
                and self._session_time is not None
                and abs(self._session_impedance_at - self._session_time)
                <= _SAME_SESSION_WINDOW
            ):
                body_measurement = BodyMeasurement(
                    self._session_weight,
                    self._session_impedance,
                    self._session_time,
                )
            updated = replace(
                previous,
                real_time_weight_kg=(
                    event.weight_kg
                    if event.weight_kg is not None
                    else previous.real_time_weight_kg
                ),
                weight_kg=(
                    event.weight_kg
                    if event.weight_kg is not None
                    else previous.weight_kg
                ),
                impedance_ohm=(
                    event.impedance_ohm
                    if event.impedance_ohm is not None
                    else previous.impedance_ohm
                ),
                heart_rate_bpm=(
                    event.heart_rate_bpm
                    if event.heart_rate_bpm is not None
                    else previous.heart_rate_bpm
                ),
                battery_percent=(
                    event.battery_percent
                    if event.battery_percent is not None
                    else previous.battery_percent
                ),
                last_measurement_at=self._session_time or previous.last_measurement_at,
                packet_status=event.status or event.phase.value,
                sequence=event.sequence
                if event.sequence is not None
                else previous.sequence,
                body_measurement=body_measurement,
            )
        if has_measurement:
            self._session_phase = event.phase
        if updated == previous:
            return False
        self._state = updated
        for callback in tuple(self._callbacks):
            callback(updated)
        return True

    def _should_begin_without_live(self, event: MeasurementEvent) -> bool:
        if not self._session_finalized or event.weight_kg is None:
            return False
        # A changed final weight cannot inherit impedance from the old weight,
        # even when no intervening live advertisement was received.
        return event.weight_kg != self._session_weight or (
            event.phase is MeasurementPhase.LOCKED
            and self._session_phase
            not in {MeasurementPhase.LIVE, MeasurementPhase.LOCKED}
        )
