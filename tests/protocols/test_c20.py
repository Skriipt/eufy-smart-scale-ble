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
