from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.onebyone import (
    OnebyoneAdvertisementParser,
    parse_onebyone_gatt,
    xor_checksum,
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


def test_short_wrong_prefix_invalid_weight_and_error_status_are_rejected() -> None:
    assert parse_onebyone_gatt(bytes(10)) is None

    wrong_prefix = bytearray(
        build_onebyone_frame(weight_hundredths=6432, final=True)
    )
    wrong_prefix[0] = 0xCE
    wrong_prefix[-1] = xor_checksum(wrong_prefix[:-1])
    assert parse_onebyone_gatt(bytes(wrong_prefix)) is None

    assert parse_onebyone_gatt(
        build_onebyone_frame(weight_hundredths=0, final=True)
    ) is None

    error_frame = bytearray(
        build_onebyone_frame(weight_hundredths=6432, final=True)
    )
    error_frame[9] = 0x02
    error_frame[-1] = xor_checksum(error_frame[:-1])
    assert parse_onebyone_gatt(bytes(error_frame)) is None


def test_live_gatt_frame_without_impedance() -> None:
    event = parse_onebyone_gatt(
        build_onebyone_frame(
            weight_hundredths=6432,
            final=False,
            impedance_present=False,
        )
    )
    assert event is not None
    assert event.phase is MeasurementPhase.LIVE
    assert event.impedance_ohm is None


def test_invalid_impedance_does_not_discard_valid_live_weight() -> None:
    event = parse_onebyone_gatt(
        build_onebyone_frame(
            weight_hundredths=6432,
            impedance_tenths=100,
            final=False,
        )
    )
    assert event is not None
    assert event.phase is MeasurementPhase.LIVE
    assert event.weight_kg == 64.32
    assert event.impedance_ohm is None


def test_advertisement_parser_ignores_non_frames_and_invalid_frames() -> None:
    invalid_measurement = build_onebyone_advertisement(
        weight_hundredths=0,
        final=True,
    )
    parser = OnebyoneAdvertisementParser()
    assert parser.parse(
        {
            1: "not-bytes",
            2: bytes(17),
            3: bytes(18),
            4: invalid_measurement,
        }
    ) == ()
