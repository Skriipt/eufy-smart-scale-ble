"""Explicit, memory-only raw protocol capture for advanced debugging."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class ProtocolCapture:
    enabled: bool = False
    max_frames: int = 100
    _frames: deque[bytes] = field(init=False)

    def __post_init__(self) -> None:
        self._frames = deque(maxlen=self.max_frames)

    def add(self, raw: object) -> None:
        if self.enabled and isinstance(raw, (bytes, bytearray, memoryview)):
            self._frames.append(bytes(raw))

    @property
    def frames(self) -> tuple[bytes, ...]:
        return tuple(self._frames)

    def clear(self) -> None:
        self._frames.clear()
