"""Tests for the Eufy P3 weighing-session state machine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.eufy_p3_ble.body_composition import BodyMeasurement
from custom_components.eufy_p3_ble.device import EufyP3Device
from custom_components.eufy_p3_ble.models import PacketStatus
from tests.fixtures.t9150_packets import (
    FINAL_82_75,
    HEART_RATE_82_75,
    IMPEDANCE_82_75,
    LIVE_82_71,
    make_packet,
)


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


def test_live_weight_does_not_create_completed_measurement() -> None:
    device = EufyP3Device()
    assert device.process({1: LIVE_82_71})
    assert device.state.real_time_weight_kg == 82.71
    assert device.state.weight_kg is None
    assert device.state.last_measurement_at is None
    assert device.state.body_measurement is None


def test_final_weight_sets_timestamp_once_per_session() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: LIVE_82_71})
    device.process({1: FINAL_82_75})
    first_time = device.state.last_measurement_at
    assert first_time == clock.value
    clock.value += timedelta(seconds=10)
    device.process({1: IMPEDANCE_82_75})
    assert device.state.last_measurement_at == first_time
    assert device.state.body_measurement == BodyMeasurement(82.75, 435.0, first_time)


def test_post_final_packets_merge_ancillary_values() -> None:
    device = EufyP3Device()
    device.process({1: FINAL_82_75})
    device.process({1: IMPEDANCE_82_75})
    device.process({1: HEART_RATE_82_75})
    assert device.state.weight_kg == 82.75
    assert device.state.impedance_ohm == 435.0
    assert device.state.heart_rate_bpm == 72


def test_missing_ancillary_value_does_not_clear_previous_value() -> None:
    device = EufyP3Device()
    device.process({1: IMPEDANCE_82_75})
    later_without_impedance = make_packet(sequence=0x5D, status=0x65)
    device.process({1: later_without_impedance})
    assert device.state.impedance_ohm == 435.0


def test_stale_callback_is_ignored() -> None:
    device = EufyP3Device()
    assert device.process({1: FINAL_82_75})
    snapshot = device.state
    assert not device.process({1: LIVE_82_71})
    assert device.state == snapshot


def test_same_sequence_lower_status_is_ignored() -> None:
    device = EufyP3Device()
    final = make_packet(sequence=9, status=0x05)
    live = make_packet(sequence=9, status=0x01)
    assert device.process({1: final})
    assert not device.process({1: live})
    assert device.state.packet_status is PacketStatus.LOCKED


def test_new_live_session_keeps_previous_completed_values() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: HEART_RATE_82_75})
    old_timestamp = device.state.last_measurement_at
    old_measurement = device.state.body_measurement
    next_live = make_packet(sequence=0x62, status=0x01, weight_kg=83.0)
    device.process({1: next_live})
    assert device.state.real_time_weight_kg == 83.0
    assert device.state.weight_kg == 82.75
    assert device.state.last_measurement_at == old_timestamp
    assert device.state.body_measurement == old_measurement


def test_new_session_final_gets_new_timestamp() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: FINAL_82_75})
    old_timestamp = device.state.last_measurement_at
    clock.value += timedelta(days=1)
    device.process({1: make_packet(sequence=0x62, status=0x01, weight_kg=83.0)})
    device.process({1: make_packet(sequence=0x63, status=0x05, weight_kg=83.05)})
    assert device.state.weight_kg == 83.05
    assert device.state.last_measurement_at == clock.value
    assert device.state.last_measurement_at != old_timestamp


def test_new_weight_cannot_reuse_previous_session_impedance() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: HEART_RATE_82_75})
    previous_measurement = device.state.body_measurement

    clock.value += timedelta(days=1)
    device.process({1: make_packet(sequence=0x62, status=0x01, weight_kg=83.0)})
    device.process({1: make_packet(sequence=0x63, status=0x05, weight_kg=83.05)})

    assert device.state.weight_kg == 83.05
    assert device.state.impedance_ohm == 435.0
    assert device.state.body_measurement == previous_measurement

    device.process(
        {
            1: make_packet(
                sequence=0x64,
                status=0x25,
                weight_kg=83.05,
                impedance_ohm=450.0,
            )
        }
    )
    assert device.state.body_measurement == BodyMeasurement(83.05, 450.0, clock.value)


def test_locked_packet_after_complete_starts_new_session_when_live_was_missed() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: HEART_RATE_82_75})
    old_measurement = device.state.body_measurement

    clock.value += timedelta(hours=1)
    device.process({1: make_packet(sequence=0x70, status=0x05, weight_kg=84.0)})
    assert device.state.body_measurement == old_measurement
    assert device.state.last_measurement_at == clock.value

    device.process(
        {
            1: make_packet(
                sequence=0x71,
                status=0x25,
                weight_kg=84.0,
                impedance_ohm=460.0,
            )
        }
    )
    assert device.state.body_measurement == BodyMeasurement(84.0, 460.0, clock.value)


def test_post_lock_packet_starts_new_session_when_early_phases_were_missed() -> None:
    clock = Clock()
    device = EufyP3Device(now=clock)
    device.process({1: HEART_RATE_82_75})
    old_measurement = device.state.body_measurement

    clock.value += timedelta(hours=1)
    device.process(
        {
            1: make_packet(
                sequence=0x70,
                status=0x25,
                weight_kg=84.0,
                impedance_ohm=460.0,
            )
        }
    )

    assert device.state.body_measurement != old_measurement
    assert device.state.body_measurement == BodyMeasurement(84.0, 460.0, clock.value)
    assert device.state.last_measurement_at == clock.value


def test_restored_measurement_seeds_completed_state() -> None:
    restored = BodyMeasurement(81.2, 440.0, datetime(2026, 8, 23, tzinfo=UTC))
    device = EufyP3Device(restored_measurement=restored)

    assert device.state.weight_kg == 81.2
    assert device.state.impedance_ohm == 440.0
    assert device.state.last_measurement_at == restored.measured_at
    assert device.state.body_measurement == restored
    assert device.state.real_time_weight_kg is None


def test_callback_registration_and_unregistration() -> None:
    device = EufyP3Device()
    states = []
    unsubscribe = device.register_callback(states.append)
    device.process({1: LIVE_82_71})
    assert len(states) == 1
    unsubscribe()
    unsubscribe()
    device.process({1: FINAL_82_75})
    assert len(states) == 1


def test_invalid_advertisement_does_not_notify() -> None:
    device = EufyP3Device()
    calls = []
    device.register_callback(calls.append)
    assert not device.process({1: b"invalid"})
    assert calls == []
