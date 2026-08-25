from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.legacy_t9140 import (
    parse_t9140_frame,
    split_notifications,
)
from tests.fixtures.builders import build_t9140_impedance, build_t9140_weight


def test_dynamic_and_final_weight() -> None:
    live = parse_t9140_frame(build_t9140_weight(weight_tenths=643, final=False))
    final = parse_t9140_frame(build_t9140_weight(weight_tenths=644, final=True))
    assert live is not None and live.phase is MeasurementPhase.LIVE
    assert final is not None and final.phase is MeasurementPhase.LOCKED


def test_impedance_is_opt_in() -> None:
    raw = build_t9140_impedance(impedance_ohm=543)
    assert parse_t9140_frame(raw, allow_impedance=False) is None
    event = parse_t9140_frame(raw, allow_impedance=True)
    assert event is not None and event.impedance_ohm == 543.0


def test_multiplex_frames_split() -> None:
    raw = b"\xac\x02" + bytes(14)
    assert len(split_notifications(raw)) == 2


def test_seventeen_byte_multiplex_frame_uses_alternate_split() -> None:
    raw = b"\xac\x02" + bytes(range(15))
    assert split_notifications(raw) == (raw[9:16], raw[0:9])


def test_non_multiplex_and_unrecognized_lengths_pass_through() -> None:
    plain = bytes(range(8))
    unexpected = b"\xac\x02" + bytes(13)
    assert split_notifications(plain) == (plain,)
    assert split_notifications(unexpected) == (unexpected,)


def test_short_unknown_and_invalid_weight_frames_are_rejected() -> None:
    unknown = bytearray(8)
    unknown[6] = 0xAA
    assert parse_t9140_frame(bytes(6)) is None
    assert parse_t9140_frame(bytes(unknown)) is None
    assert parse_t9140_frame(build_t9140_weight(weight_tenths=0, final=True)) is None


def test_invalid_impedance_is_rejected_when_opted_in() -> None:
    raw = build_t9140_impedance(impedance_ohm=0)
    assert parse_t9140_frame(raw, allow_impedance=True) is None
