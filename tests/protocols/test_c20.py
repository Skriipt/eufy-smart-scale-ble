from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.c20 import C20AdvertisementParser
from tests.fixtures.builders import build_c20_packet


def test_weight_impedance_and_hr_are_decoded() -> None:
    packet = build_c20_packet(
        flags=0xC5,
        weight_hundredths=6432,
        impedance_tenths=5432,
        heart_rate=88,
    )
    event = C20AdvertisementParser().parse({1: packet})[0]
    assert event.phase is MeasurementPhase.LOCKED
    assert event.weight_kg == 64.32
    assert event.impedance_ohm == 543.2
    assert event.heart_rate_bpm == 88


def test_unknown_empty_packet_is_ignored() -> None:
    assert C20AdvertisementParser().parse({1: bytes(23)}) == ()


def test_non_binary_and_short_payloads_are_ignored() -> None:
    parser = C20AdvertisementParser()
    assert parser.parse({1: "not-bytes", 2: bytes(13)}) == ()


def test_invalid_measurement_fields_are_ignored() -> None:
    packet = build_c20_packet(
        flags=0xC1,
        weight_hundredths=0,
        impedance_tenths=0,
        heart_rate=10,
    )
    assert C20AdvertisementParser().parse({1: packet}) == ()


def test_impedance_only_packet_uses_impedance_phase() -> None:
    packet = build_c20_packet(flags=0x40, impedance_tenths=5432)
    event = C20AdvertisementParser().parse({1: packet})[0]
    assert event.phase is MeasurementPhase.IMPEDANCE
    assert event.weight_kg is None
    assert event.impedance_ohm == 543.2


def test_live_weight_and_heart_rate_are_preserved() -> None:
    packet = build_c20_packet(flags=0x81, weight_hundredths=6432, heart_rate=88)
    event = C20AdvertisementParser().parse({1: packet})[0]
    assert event.phase is MeasurementPhase.LIVE
    assert event.weight_kg == 64.32
    assert event.heart_rate_bpm == 88


def test_truncated_optional_fields_are_ignored() -> None:
    impedance_packet = build_c20_packet(flags=0x40, impedance_tenths=5432)[:16]
    heart_rate_packet = build_c20_packet(flags=0x80, heart_rate=88)[:15]
    parser = C20AdvertisementParser()
    assert parser.parse({1: impedance_packet}) == ()
    assert parser.parse({1: heart_rate_packet}) == ()
