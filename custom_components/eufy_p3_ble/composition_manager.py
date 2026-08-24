"""Coordinate profile data, complete measurements, and calculated results."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

from .body_composition import (
    BodyCompositionProfile,
    BodyCompositionResult,
    BodyMeasurement,
    calculate_body_composition,
)

CompositionCallback = Callable[[BodyCompositionResult | None], None]


class BodyCompositionManager:
    """Keep the latest raw measurement and its locally calculated result."""

    def __init__(
        self,
        *,
        profile: BodyCompositionProfile | None,
        measurement: BodyMeasurement | None = None,
    ) -> None:
        self._profile = profile
        self._measurement = measurement
        self._result = self._calculate()
        self._callbacks: list[CompositionCallback] = []

    @property
    def profile(self) -> BodyCompositionProfile | None:
        """Return the configured calculation profile."""
        return self._profile

    @property
    def measurement(self) -> BodyMeasurement | None:
        """Return the latest complete same-session raw measurement."""
        return self._measurement

    @property
    def result(self) -> BodyCompositionResult | None:
        """Return the latest locally calculated body-composition result."""
        return self._result

    def register_callback(self, callback: CompositionCallback) -> Callable[[], None]:
        """Register a result callback and return an idempotent unsubscribe call."""
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

    def update_profile(self, profile: BodyCompositionProfile | None) -> bool:
        """Update the personal profile and recalculate the current measurement."""
        if profile == self._profile:
            return False
        self._profile = profile
        self._result = self._calculate()
        self._notify()
        return True

    def update_measurement(self, measurement: BodyMeasurement) -> bool:
        """Accept a new complete raw measurement and recalculate it."""
        if measurement == self._measurement:
            return False
        self._measurement = measurement
        self._result = self._calculate()
        self._notify()
        return True

    def _calculate(self) -> BodyCompositionResult | None:
        if self._profile is None or self._measurement is None:
            return None
        try:
            return calculate_body_composition(self._profile, self._measurement)
        except ValueError:
            return None

    def _notify(self) -> None:
        for callback in tuple(self._callbacks):
            callback(self._result)
