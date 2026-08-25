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
