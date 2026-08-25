import pytest

from custom_components.eufy_smart_scale_ble.protocols.p2 import (
    P2AuthSession,
    _encrypt,
    key_from_mac,
    parse_p2_advertisement,
    segment,
)
from tests.fixtures.builders import build_p2_advertisement

SYNTHETIC_ADDRESS = ":".join(("02", "00", "00", "00", "00", "01"))


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
