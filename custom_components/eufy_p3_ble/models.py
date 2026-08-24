"""Pure data models for Eufy Smart Scale P3 BLE advertisements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .device import EufyP3Device


class PacketStatus(IntEnum):
    """Known T9150 weighing phases."""

    LIVE = 0x01
    LOCKED = 0x05
    POST_LOCK = 0x15
    IMPEDANCE = 0x25
    BODY_COMPOSITION = 0x65
    BODY_COMPOSITION_LATE = 0xA5
    COMPLETE = 0xE5

    @property
    def slug(self) -> str:
        """Return a stable Home Assistant-friendly state string."""
        return {
            PacketStatus.LIVE: "live",
            PacketStatus.LOCKED: "locked",
            PacketStatus.POST_LOCK: "post_lock",
            PacketStatus.IMPEDANCE: "impedance",
            PacketStatus.BODY_COMPOSITION: "body_composition",
            PacketStatus.BODY_COMPOSITION_LATE: "body_composition_late",
            PacketStatus.COMPLETE: "complete",
        }[self]

    @property
    def rank(self) -> int:
        """Return protocol progression rank for equal sequence counters."""
        return tuple(PacketStatus).index(self)

    @property
    def is_final(self) -> bool:
        """Return whether this phase belongs to a locked measurement."""
        return self is not PacketStatus.LIVE


@dataclass(frozen=True, slots=True)
class ScaleFrame:
    """One validated T9150 manufacturer-data frame."""

    raw: bytes
    sequence: int
    status: PacketStatus
    weight_kg: float
    heart_rate_bpm: int | None = None
    impedance_ohm: float | None = None

    @property
    def is_final(self) -> bool:
        """Return whether this frame belongs to a completed weighing session."""
        return self.status.is_final


@dataclass(frozen=True, slots=True)
class ScaleState:
    """Merged current and last-completed scale state."""

    real_time_weight_kg: float | None = None
    weight_kg: float | None = None
    impedance_ohm: float | None = None
    heart_rate_bpm: int | None = None
    last_measurement_at: datetime | None = None
    packet_status: PacketStatus | None = None
    sequence: int | None = None
    raw_packet_hex: str | None = None


@dataclass(slots=True)
class EufyP3RuntimeData:
    """Runtime data stored on the Home Assistant config entry."""

    address: str
    device: EufyP3Device
