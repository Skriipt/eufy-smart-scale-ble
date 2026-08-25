"""Regression tests for the hardware-verified P3 parser."""

import pytest

from custom_components.eufy_smart_scale_ble.protocols.base import MeasurementPhase
from custom_components.eufy_smart_scale_ble.protocols.p3 import (
    P3AdvertisementParser,
    P3Status,
    is_sequence_newer,
    parse_p3_packet,
)
from tests.fixtures.t9150_packets import FINAL_SAMPLE, LIVE_SAMPLE, make_packet


def test_parse_live_weight() -> None:
    parsed = parse_p3_packet(LIVE_SAMPLE)
    assert parsed is not None
    status, event = parsed
    assert status is P3Status.LIVE
    assert event.phase is MeasurementPhase.LIVE
    assert event.sequence == 0x57
    assert event.weight_kg == 72.31


def test_parse_complete_fields() -> None:
    raw = make_packet(
        sequence=3,
        status=0xE5,
        weight_kg=64.32,
        impedance_ohm=543.2,
        heart_rate=88,
    )
    parsed = parse_p3_packet(raw)
    assert parsed is not None
    status, event = parsed
    assert status is P3Status.COMPLETE
    assert event.weight_kg == 64.32
    assert event.impedance_ohm == 543.2
    assert event.heart_rate_bpm == 88


@pytest.mark.parametrize("status", [0x15, 0x25, 0x65, 0xA5, 0xE5])
def test_all_post_lock_statuses(status: int) -> None:
    parsed = parse_p3_packet(make_packet(sequence=1, status=status))
    assert parsed is not None
    assert parsed[0].value == status


@pytest.mark.parametrize("heart_rate", [0, 29, 241, 255])
def test_invalid_heart_rate_is_ignored(heart_rate: int) -> None:
    parsed = parse_p3_packet(
        make_packet(sequence=1, status=0xE5, heart_rate=heart_rate)
    )
    assert parsed is not None
    assert parsed[1].heart_rate_bpm is None


@pytest.mark.parametrize("impedance", [0.0, 49.9, 2000.1, 4000.0])
def test_invalid_impedance_is_ignored(impedance: float) -> None:
    parsed = parse_p3_packet(
        make_packet(sequence=1, status=0x25, impedance_ohm=impedance)
    )
    assert parsed is not None
    assert parsed[1].impedance_ohm is None


@pytest.mark.parametrize("raw", [b"", b"short", bytearray(18), "bad", None])
def test_invalid_input_is_rejected(raw: object) -> None:
    assert parse_p3_packet(raw) is None


def test_unknown_status_is_rejected() -> None:
    assert parse_p3_packet(make_packet(sequence=1, status=0x45)) is None


@pytest.mark.parametrize("weight", [0.0, -1.0, 200.01, 300.0])
def test_invalid_weight_is_rejected(weight: float) -> None:
    assert parse_p3_packet(
        make_packet(sequence=1, status=0x01, weight_kg=weight)
    ) is None


@pytest.mark.parametrize(
    ("candidate", "reference", "expected"),
    [(1, 0, True), (0, 255, True), (255, 0, False), (0, 0, False), (128, 0, False)],
)
def test_sequence_comparison(candidate: int, reference: int, expected: bool) -> None:
    assert is_sequence_newer(candidate, reference) is expected


def test_parser_rejects_duplicate_and_stale_packets() -> None:
    parser = P3AdvertisementParser()
    assert parser.parse({1: FINAL_SAMPLE})
    assert parser.parse({1: FINAL_SAMPLE}) == ()
    assert parser.parse({1: LIVE_SAMPLE}) == ()
