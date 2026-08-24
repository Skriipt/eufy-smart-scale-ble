"""Tests for the pure T9150 parser."""

from __future__ import annotations

import pytest

from custom_components.eufy_p3_ble.models import PacketStatus
from custom_components.eufy_p3_ble.parser import is_sequence_newer, parse_frame
from tests.fixtures.t9150_packets import FINAL_82_75, LIVE_82_71, make_packet


def test_parse_live_weight() -> None:
    frame = parse_frame(LIVE_82_71)
    assert frame is not None
    assert frame.sequence == 0x57
    assert frame.status is PacketStatus.LIVE
    assert frame.weight_kg == 82.71
    assert frame.heart_rate_bpm is None
    assert frame.impedance_ohm is None


def test_parse_locked_weight() -> None:
    frame = parse_frame(FINAL_82_75)
    assert frame is not None
    assert frame.status is PacketStatus.LOCKED
    assert frame.weight_kg == 82.75
    assert frame.is_final


@pytest.mark.parametrize("status", [0x15, 0x25, 0x65, 0xA5, 0xE5])
def test_parse_all_post_final_statuses(status: int) -> None:
    frame = parse_frame(make_packet(sequence=1, status=status))
    assert frame is not None
    assert frame.status.value == status
    assert frame.is_final


def test_parse_impedance() -> None:
    frame = parse_frame(make_packet(sequence=2, status=0x25, impedance_ohm=435.0))
    assert frame is not None
    assert frame.impedance_ohm == 435.0


def test_parse_heart_rate() -> None:
    frame = parse_frame(make_packet(sequence=3, status=0xE5, heart_rate=72))
    assert frame is not None
    assert frame.heart_rate_bpm == 72


@pytest.mark.parametrize("heart_rate", [0, 29, 241, 255])
def test_ignore_implausible_heart_rate(heart_rate: int) -> None:
    frame = parse_frame(make_packet(sequence=3, status=0xE5, heart_rate=heart_rate))
    assert frame is not None
    assert frame.heart_rate_bpm is None


@pytest.mark.parametrize("impedance", [0.0, 49.9, 2000.1, 4000.0])
def test_ignore_implausible_impedance(impedance: float) -> None:
    frame = parse_frame(make_packet(sequence=3, status=0x25, impedance_ohm=impedance))
    assert frame is not None
    assert frame.impedance_ohm is None


@pytest.mark.parametrize("raw", [b"", b"short", bytearray(18), "not-bytes", None])
def test_reject_invalid_input(raw: object) -> None:
    assert parse_frame(raw) is None


def test_reject_unknown_status() -> None:
    assert parse_frame(make_packet(sequence=1, status=0x45)) is None


@pytest.mark.parametrize("weight", [0.0, -1.0, 200.01, 300.0])
def test_reject_implausible_weight(weight: float) -> None:
    raw = make_packet(sequence=1, status=0x01, weight_kg=weight)
    assert parse_frame(raw) is None


@pytest.mark.parametrize(
    ("candidate", "reference", "expected"),
    [
        (1, 0, True),
        (0, 255, True),
        (255, 0, False),
        (0, 0, False),
        (128, 0, False),
    ],
)
def test_sequence_comparison(candidate: int, reference: int, expected: bool) -> None:
    assert is_sequence_newer(candidate, reference) is expected
