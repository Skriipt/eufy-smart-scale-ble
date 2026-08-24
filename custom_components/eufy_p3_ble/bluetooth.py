"""Helpers for selecting current data from BLE manufacturer entries."""

from __future__ import annotations

from collections.abc import Mapping

from .models import ScaleFrame
from .parser import is_sequence_newer, parse_frame


def _candidate_wins(candidate: ScaleFrame, current: ScaleFrame) -> bool:
    """Return whether candidate should replace current selection."""
    if is_sequence_newer(candidate.sequence, current.sequence):
        return True
    if candidate.sequence != current.sequence:
        return False
    return candidate.status.rank > current.status.rank


def select_newest_frame(manufacturer_data: Mapping[int, object]) -> ScaleFrame | None:
    """Parse all manufacturer values and return the newest valid T9150 frame."""
    selected: ScaleFrame | None = None
    seen: set[bytes] = set()

    for raw in manufacturer_data.values():
        frame = parse_frame(raw)
        if frame is None or frame.raw in seen:
            continue
        seen.add(frame.raw)
        if selected is None or _candidate_wins(frame, selected):
            selected = frame

    return selected
