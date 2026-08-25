"""Privacy-safe Home Assistant diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .model_registry import Capability
from .protocols.base import MeasurementEvent


@dataclass(slots=True)
class RuntimeDiagnostics:
    advertisements_seen: int = 0
    accepted_events: int = 0
    packet_lengths: Counter[int] = field(default_factory=Counter)
    statuses: Counter[str] = field(default_factory=Counter)
    gatt_connections: int = 0
    gatt_failures: int = 0

    def record_advertisement(self, values: object) -> None:
        self.advertisements_seen += 1
        if isinstance(values, dict):
            for raw in values.values():
                if isinstance(raw, (bytes, bytearray, memoryview)):
                    self.packet_lengths[len(raw)] += 1

    def record_event(self, event: MeasurementEvent) -> None:
        self.accepted_events += 1
        self.statuses[event.status or event.phase.value] += 1


async def async_get_config_entry_diagnostics(_hass: Any, entry: Any) -> dict[str, Any]:
    data = entry.runtime_data
    model = data.model
    stats = data.diagnostics
    return {
        "model": model.model_name,
        "protocol_family": model.protocol_family,
        "transport": model.transport.value,
        "capabilities": {
            capability.value: model.capability(capability).level.value
            for capability in Capability
        },
        "runtime": {
            "advertisements_seen": stats.advertisements_seen,
            "accepted_events": stats.accepted_events,
            "packet_lengths_seen": sorted(stats.packet_lengths),
            "parser_statuses_seen": sorted(stats.statuses),
            "gatt_connections": stats.gatt_connections,
            "gatt_failures": stats.gatt_failures,
        },
    }
