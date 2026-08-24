"""Tests for newest T9150 advertisement selection."""

from __future__ import annotations

from custom_components.eufy_p3_ble.bluetooth import select_newest_frame
from custom_components.eufy_p3_ble.models import PacketStatus
from tests.fixtures.t9150_packets import FINAL_82_75, LIVE_82_71, make_packet


def test_selects_newer_final_packet_after_stale_live_packet() -> None:
    frame = select_newest_frame({53075: LIVE_82_71, 53085: FINAL_82_75})
    assert frame is not None
    assert frame.status is PacketStatus.LOCKED
    assert frame.weight_kg == 82.75


def test_mapping_order_does_not_override_sequence() -> None:
    frame = select_newest_frame({53085: FINAL_82_75, 53075: LIVE_82_71})
    assert frame is not None
    assert frame.status is PacketStatus.LOCKED


def test_deduplicates_identical_packets() -> None:
    frame = select_newest_frame({1: FINAL_82_75, 2: FINAL_82_75})
    assert frame is not None
    assert frame.raw == FINAL_82_75


def test_equal_sequence_prefers_more_advanced_status() -> None:
    live = make_packet(sequence=9, status=0x01, weight_kg=82.7)
    final = make_packet(sequence=9, status=0x05, weight_kg=82.75)
    frame = select_newest_frame({1: live, 2: final})
    assert frame is not None
    assert frame.status is PacketStatus.LOCKED


def test_sequence_wraparound() -> None:
    older = make_packet(sequence=255, status=0x01)
    newer = make_packet(sequence=0, status=0x05)
    frame = select_newest_frame({1: older, 2: newer})
    assert frame is not None
    assert frame.sequence == 0


def test_invalid_entries_are_ignored() -> None:
    frame = select_newest_frame({1: b"bad", 2: FINAL_82_75})
    assert frame is not None
    assert frame.status is PacketStatus.LOCKED


def test_no_valid_entries_returns_none() -> None:
    assert select_newest_frame({1: b"bad", 2: b"also bad"}) is None
