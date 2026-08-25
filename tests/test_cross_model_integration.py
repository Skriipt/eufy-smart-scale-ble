"""Architecture-neutral cross-model protocol/session regressions."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.eufy_smart_scale_ble.body_composition import BodyMeasurement
from custom_components.eufy_smart_scale_ble.device import EufyScaleDevice
from custom_components.eufy_smart_scale_ble.protocols.c20 import C20AdvertisementParser
from custom_components.eufy_smart_scale_ble.protocols.legacy_t9140 import (
    parse_t9140_frame,
)
from custom_components.eufy_smart_scale_ble.protocols.onebyone import (
    OnebyoneAdvertisementParser,
    parse_onebyone_gatt,
)
from custom_components.eufy_smart_scale_ble.protocols.p2 import parse_p2_advertisement
from custom_components.eufy_smart_scale_ble.protocols.p3 import P3AdvertisementParser
from tests.fixtures.builders import (
    build_c20_packet,
    build_onebyone_advertisement,
    build_onebyone_frame,
    build_p2_advertisement,
    build_p3_packet,
    build_t9140_weight,
)

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def device() -> EufyScaleDevice:
    return EufyScaleDevice(now=lambda: NOW)


def test_p3_passive_complete_session_preserves_full_raw_fields() -> None:
    parser = P3AdvertisementParser()
    scale = device()
    packets = (
        build_p3_packet(sequence=1, status=0x01, weight_hundredths=6430),
        build_p3_packet(sequence=2, status=0x05, weight_hundredths=6432),
        build_p3_packet(
            sequence=3,
            status=0xE5,
            weight_hundredths=6432,
            impedance_tenths=5432,
            heart_rate=88,
        ),
    )
    for packet in packets:
        for event in parser.parse({1: packet}):
            scale.process_event(event)
    assert scale.state.weight_kg == 64.32
    assert scale.state.impedance_ohm == 543.2
    assert scale.state.heart_rate_bpm == 88
    assert scale.state.body_measurement == BodyMeasurement(64.32, 543.2, NOW)


def test_c20_passive_weight_impedance_and_heart_rate_complete_session() -> None:
    parser = C20AdvertisementParser()
    scale = device()
    for raw in (
        build_c20_packet(flags=0x01, weight_hundredths=6430),
        build_c20_packet(
            flags=0xC5,
            weight_hundredths=6432,
            impedance_tenths=5432,
            heart_rate=88,
        ),
    ):
        for event in parser.parse({1: raw}):
            scale.process_event(event)
    assert scale.state.weight_kg == 64.32
    assert scale.state.impedance_ohm == 543.2
    assert scale.state.heart_rate_bpm == 88
    assert scale.state.body_measurement == BodyMeasurement(64.32, 543.2, NOW)


def test_c1_passive_weight_does_not_invent_impedance() -> None:
    event = OnebyoneAdvertisementParser().parse(
        {
            1: build_onebyone_advertisement(
                weight_hundredths=6432,
                final=True,
                impedance_tenths=5432,
            )
        }
    )[0]
    assert event.weight_kg == 64.32
    assert event.impedance_ohm is None


def test_c1_optional_gatt_can_enrich_same_session() -> None:
    scale = device()
    passive = OnebyoneAdvertisementParser().parse(
        {
            1: build_onebyone_advertisement(
                weight_hundredths=6432,
                final=True,
                impedance_tenths=5432,
            )
        }
    )[0]
    scale.process_event(passive)
    enriched = parse_onebyone_gatt(
        build_onebyone_frame(
            weight_hundredths=6432,
            impedance_tenths=5432,
            final=True,
        )
    )
    assert enriched is not None
    scale.process_event(enriched)
    assert scale.state.body_measurement == BodyMeasurement(64.32, 543.2, NOW)


def test_a1_gatt_frame_provides_weight_and_impedance() -> None:
    event = parse_onebyone_gatt(
        build_onebyone_frame(
            weight_hundredths=6432,
            impedance_tenths=5432,
            final=True,
        )
    )
    assert event is not None
    assert event.weight_kg == 64.32
    assert event.impedance_ohm == 543.2


def test_t9140_gatt_dynamic_then_stable_weight() -> None:
    scale = device()
    live = parse_t9140_frame(build_t9140_weight(weight_tenths=643, final=False))
    final = parse_t9140_frame(build_t9140_weight(weight_tenths=644, final=True))
    assert live is not None and final is not None
    scale.process_event(live)
    scale.process_event(final)
    assert scale.state.real_time_weight_kg == 64.4
    assert scale.state.weight_kg == 64.4


def test_p2_passive_weight_never_produces_impedance() -> None:
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


def test_p2_pro_passive_weight_and_heart_rate_without_impedance() -> None:
    event = parse_p2_advertisement(
        build_p2_advertisement(
            weight_hundredths=6432,
            final=True,
            heart_rate=88,
            opaque_field=0xFEDCBA,
        ),
        supports_heart_rate=True,
    )
    assert event is not None
    assert event.heart_rate_bpm == 88
    assert event.impedance_ohm is None


def test_restart_restores_only_explicit_complete_measurement() -> None:
    restored = BodyMeasurement(64.32, 543.2, NOW)
    scale = EufyScaleDevice(restored_measurement=restored)
    assert scale.state.body_measurement == restored
    assert scale.state.real_time_weight_kg is None
