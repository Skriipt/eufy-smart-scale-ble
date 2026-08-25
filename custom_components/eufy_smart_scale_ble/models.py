"""Runtime data models for Eufy Smart Scale BLE."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .body_composition import BodyMeasurement

if TYPE_CHECKING:
    from .composition_manager import BodyCompositionManager
    from .device import EufyScaleDevice
    from .diagnostics import RuntimeDiagnostics
    from .gatt import EufyGattSession
    from .model_registry import ScaleModelDefinition
    from .protocol_capture import ProtocolCapture


@dataclass(frozen=True, slots=True)
class ScaleState:
    real_time_weight_kg: float | None = None
    weight_kg: float | None = None
    impedance_ohm: float | None = None
    heart_rate_bpm: int | None = None
    battery_percent: int | None = None
    last_measurement_at: datetime | None = None
    packet_status: str | None = None
    sequence: int | None = None
    body_measurement: BodyMeasurement | None = None


@dataclass(slots=True)
class EufyScaleRuntimeData:
    address: str
    model: ScaleModelDefinition
    device: EufyScaleDevice
    composition: BodyCompositionManager
    diagnostics: RuntimeDiagnostics
    capture: ProtocolCapture
    gatt: EufyGattSession | None = None
