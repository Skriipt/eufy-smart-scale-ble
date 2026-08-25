import pytest

from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.p2 import (
    P2AuthSession,
    _encrypt,
    key_from_mac,
    parse_p2_advertisement,
    parse_p2_gatt_weight,
    segment,
)
from tests.fixtures.builders import build_p2_advertisement

SYNTHETIC_ADDRESS = ":".join(("02", "00", "00", "00", "00", "01"))


def _build_p2_gatt_weight(*, weight_hundredths: int, final: bool) -> bytes:
    data = bytearray(16)
    data[0] = 0xCF
    data[2] = 0
    data[6:8] = weight_hundredths.to_bytes(2, "little")
    data[12] = 0 if final else 1
    return bytes(data)


def test_p2_weight_does_not_expose_opaque_field_as_impedance() -> None:
    event = parse_p2_advertisement(
        build_p2_advertisement(
            weight_hundredths=6432,
            final=True,
            opaque_field=0xFEDCBA,
        ),
        supports_heart_rate=False,
    )
    assert event is not None
    assert event.weight_kg == 64.32
    assert event.impedance_ohm is None


def test_p2_pro_heart_rate_is_model_gated() -> None:
    raw = build_p2_advertisement(weight_hundredths=6432, final=True, heart_rate=88)
    assert parse_p2_advertisement(raw, supports_heart_rate=False).heart_rate_bpm is None
    assert parse_p2_advertisement(raw, supports_heart_rate=True).heart_rate_bpm == 88


def test_auth_key_and_segments_are_deterministic_for_synthetic_address() -> None:
    key = key_from_mac(SYNTHETIC_ADDRESS)
    assert len(key) == 16
    frames = segment("00" * 20, 0xC0)
    assert len(frames) == 2
    assert all(frame[0] == 0xC0 for frame in frames)


def test_auth_requires_valid_client_uuid() -> None:
    with pytest.raises(ValueError):
        P2AuthSession(SYNTHETIC_ADDRESS, "short")


def test_auth_c1_reassembly_and_c3_status() -> None:
    session = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    device_uuid = "device-uuid-001"
    c1_frames = segment(_encrypt(device_uuid, session.key), 0xC1)
    completed = False
    for frame in c1_frames:
        completed = session.handle_c1(frame)
    assert completed
    assert session.device_uuid == device_uuid
    assert session.c2()
    assert session.handle_c3(bytes((0xC3, 0, 0, 0, 0)))
    assert session.authenticated


def test_auth_c3_failure_is_recorded() -> None:
    session = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    assert session.handle_c3(bytes((0xC3, 0, 0, 0, 1)))
    assert not session.authenticated


def test_advertisement_rejects_bad_types_shapes_headers_and_weight() -> None:
    assert parse_p2_advertisement("not-bytes", supports_heart_rate=True) is None
    assert parse_p2_advertisement(bytes(18), supports_heart_rate=True) is None

    wrong_header = bytearray(build_p2_advertisement(weight_hundredths=6432, final=True))
    wrong_header[6] = 0
    assert parse_p2_advertisement(wrong_header, supports_heart_rate=True) is None

    invalid_weight = build_p2_advertisement(weight_hundredths=0, final=True)
    assert parse_p2_advertisement(invalid_weight, supports_heart_rate=True) is None


def test_live_advertisement_ignores_invalid_heart_rate() -> None:
    raw = build_p2_advertisement(weight_hundredths=6432, final=False, heart_rate=10)
    event = parse_p2_advertisement(raw, supports_heart_rate=True)
    assert event is not None
    assert event.phase is MeasurementPhase.LIVE
    assert event.heart_rate_bpm is None


def test_heart_rate_requires_protocol_marker() -> None:
    raw = build_p2_advertisement(weight_hundredths=6432, final=True)
    event = parse_p2_advertisement(raw, supports_heart_rate=True)
    assert event is not None
    assert event.heart_rate_bpm is None


def test_gatt_weight_supports_live_and_final_measurements() -> None:
    final = parse_p2_gatt_weight(
        _build_p2_gatt_weight(weight_hundredths=6432, final=True)
    )
    live = parse_p2_gatt_weight(
        _build_p2_gatt_weight(weight_hundredths=6433, final=False)
    )
    assert final is not None
    assert final.phase is MeasurementPhase.LOCKED
    assert final.weight_kg == 64.32
    assert live is not None
    assert live.phase is MeasurementPhase.LIVE
    assert live.weight_kg == 64.33


def test_gatt_weight_rejects_bad_shapes_headers_and_weight() -> None:
    assert parse_p2_gatt_weight(bytes(15)) is None

    wrong_header = bytearray(_build_p2_gatt_weight(weight_hundredths=6432, final=True))
    wrong_header[0] = 0
    assert parse_p2_gatt_weight(bytes(wrong_header)) is None

    wrong_kind = bytearray(_build_p2_gatt_weight(weight_hundredths=6432, final=True))
    wrong_kind[2] = 1
    assert parse_p2_gatt_weight(bytes(wrong_kind)) is None

    assert (
        parse_p2_gatt_weight(_build_p2_gatt_weight(weight_hundredths=0, final=True))
        is None
    )


def test_key_validation_rejects_bad_addresses() -> None:
    with pytest.raises(ValueError):
        key_from_mac("02:00")
    with pytest.raises(ValueError):
        key_from_mac("GG:00:00:00:00:01")


def test_auth_c0_and_c2_precondition() -> None:
    session = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    frames = session.c0()
    assert frames
    assert all(frame[0] == 0xC0 for frame in frames)
    with pytest.raises(RuntimeError):
        session.c2()


def test_auth_c1_rejects_malformed_and_out_of_order_segments() -> None:
    session = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    frames = segment(_encrypt("device-uuid-001", session.key), 0xC1)
    assert len(frames) > 1
    assert not session.handle_c1(bytes(5))

    wrong_prefix = bytearray(frames[0])
    wrong_prefix[0] = 0xC2
    assert not session.handle_c1(bytes(wrong_prefix))

    bad_checksum = bytearray(frames[0])
    bad_checksum[-1] ^= 0xFF
    assert not session.handle_c1(bytes(bad_checksum))

    out_of_order = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    assert not out_of_order.handle_c1(frames[1])


def test_auth_c3_rejects_malformed_frames() -> None:
    session = P2AuthSession(SYNTHETIC_ADDRESS, "client-uuid-001")
    assert not session.handle_c3(bytes(4))
    assert not session.handle_c3(bytes((0xC2, 0, 0, 0, 0)))
