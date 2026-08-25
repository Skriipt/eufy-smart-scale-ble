from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.onebyone import (
    OnebyoneAdvertisementParser,
    parse_onebyone_gatt,
)
from tests.fixtures.builders import build_onebyone_advertisement, build_onebyone_frame


def test_passive_c1_p1_weight() -> None:
    packet = build_onebyone_advertisement(
        weight_hundredths=6432,
        impedance_tenths=5432,
        final=True,
    )
    event = OnebyoneAdvertisementParser().parse({1: packet})[0]
    assert event.phase is MeasurementPhase.LOCKED
    assert event.weight_kg == 64.32
    assert event.impedance_ohm is None


def test_gatt_frame_adds_impedance() -> None:
    event = parse_onebyone_gatt(
        build_onebyone_frame(
            weight_hundredths=6432,
            impedance_tenths=5432,
            final=True,
        )
    )
    assert event is not None
    assert event.impedance_ohm == 543.2


def test_bad_checksum_is_rejected() -> None:
    frame = bytearray(
        build_onebyone_frame(
            weight_hundredths=6432,
            impedance_tenths=5432,
            final=True,
        )
    )
    frame[-1] ^= 0xFF
    assert parse_onebyone_gatt(bytes(frame)) is None
