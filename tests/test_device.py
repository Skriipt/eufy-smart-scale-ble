"""Generic session-state tests preserving P3 semantics."""

from datetime import UTC, datetime, timedelta

from custom_components.eufy_smart_scale_ble.body_composition import BodyMeasurement
from custom_components.eufy_smart_scale_ble.device import EufyScaleDevice
from custom_components.eufy_smart_scale_ble.protocols.base import (
    MeasurementEvent,
    MeasurementPhase,
)


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


def test_live_does_not_create_complete_measurement() -> None:
    device = EufyScaleDevice()
    device.process_event(
        MeasurementEvent(MeasurementPhase.LIVE, weight_kg=64.3, status="live")
    )
    assert device.state.real_time_weight_kg == 64.3
    assert device.state.weight_kg is None
    assert device.state.body_measurement is None


def test_same_session_weight_and_impedance_create_body_measurement() -> None:
    clock = Clock()
    device = EufyScaleDevice(now=clock)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LIVE, weight_kg=64.3, status="live")
    )
    device.process_event(
        MeasurementEvent(MeasurementPhase.LOCKED, weight_kg=64.32, status="locked")
    )
    measured_at = device.state.last_measurement_at
    clock.value += timedelta(seconds=10)
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.IMPEDANCE,
            weight_kg=64.32,
            impedance_ohm=543.2,
            status="impedance",
        )
    )
    assert device.state.body_measurement == BodyMeasurement(64.32, 543.2, measured_at)
    assert device.state.last_measurement_at == measured_at


def test_fresh_impedance_only_event_completes_current_session() -> None:
    clock = Clock()
    device = EufyScaleDevice(now=clock)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LOCKED, weight_kg=64.32, status="locked")
    )
    measured_at = device.state.last_measurement_at
    clock.value += timedelta(seconds=10)
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.IMPEDANCE,
            impedance_ohm=543.2,
            status="impedance",
        )
    )
    assert device.state.body_measurement == BodyMeasurement(64.32, 543.2, measured_at)


def test_stale_impedance_only_event_does_not_reuse_finalized_weight() -> None:
    clock = Clock()
    device = EufyScaleDevice(now=clock)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LOCKED, weight_kg=64.32, status="locked")
    )
    clock.value += timedelta(seconds=31)
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.IMPEDANCE,
            impedance_ohm=543.2,
            status="impedance",
        )
    )
    assert device.state.body_measurement is None


def test_finalized_weight_does_not_reuse_stale_impedance() -> None:
    clock = Clock()
    device = EufyScaleDevice(now=clock)
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.IMPEDANCE,
            impedance_ohm=543.2,
            status="impedance",
        )
    )
    clock.value += timedelta(seconds=31)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LOCKED, weight_kg=64.32, status="locked")
    )
    assert device.state.body_measurement is None


def test_previous_session_impedance_is_never_reused() -> None:
    clock = Clock()
    previous = BodyMeasurement(63.0, 530.0, clock.value)
    device = EufyScaleDevice(now=clock, restored_measurement=previous)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LIVE, weight_kg=65.0, status="live")
    )
    clock.value += timedelta(hours=1)
    device.process_event(
        MeasurementEvent(MeasurementPhase.LOCKED, weight_kg=65.1, status="locked")
    )
    assert device.state.body_measurement == previous
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.IMPEDANCE,
            weight_kg=65.1,
            impedance_ohm=540.0,
            status="impedance",
        )
    )
    assert device.state.body_measurement == BodyMeasurement(65.1, 540.0, clock.value)


def test_battery_and_heart_rate_enrich_state() -> None:
    device = EufyScaleDevice()
    device.process_event(
        MeasurementEvent(
            MeasurementPhase.LIVE,
            heart_rate_bpm=72,
            battery_percent=81,
            status="live",
        )
    )
    assert device.state.heart_rate_bpm == 72
    assert device.state.battery_percent == 81


def test_callbacks_are_idempotently_unsubscribed() -> None:
    device = EufyScaleDevice()
    calls = []
    unsubscribe = device.register_callback(calls.append)
    device.process_event(MeasurementEvent(MeasurementPhase.LIVE, weight_kg=60.0))
    assert len(calls) == 1
    unsubscribe()
    unsubscribe()
    device.process_event(MeasurementEvent(MeasurementPhase.LIVE, weight_kg=61.0))
    assert len(calls) == 1
