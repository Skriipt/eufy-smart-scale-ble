"""Supported Eufy scale models and per-capability support."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class SupportLevel(StrEnum):
    VERIFIED = "verified"
    UPSTREAM_VALIDATED = "upstream_validated"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class Capability(StrEnum):
    LIVE_WEIGHT = "live_weight"
    FINAL_WEIGHT = "final_weight"
    IMPEDANCE = "impedance"
    HEART_RATE = "heart_rate"
    BATTERY = "battery"
    BODY_COMPOSITION = "body_composition"


class TransportMode(StrEnum):
    ADVERTISEMENT = "advertisement"
    GATT = "gatt"
    ADVERTISEMENT_WITH_OPTIONAL_GATT = "advertisement_with_optional_gatt"


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    level: SupportLevel
    enabled_by_default: bool = True


@dataclass(frozen=True, slots=True)
class ScaleModelDefinition:
    model_id: str
    display_name: str
    model_name: str
    protocol_family: str
    transport: TransportMode
    capabilities: Mapping[Capability, CapabilityDefinition]

    def capability(self, capability: Capability) -> CapabilityDefinition:
        return self.capabilities.get(
            capability,
            CapabilityDefinition(SupportLevel.UNSUPPORTED, False),
        )


def _caps(
    **values: tuple[SupportLevel, bool] | SupportLevel,
) -> Mapping[Capability, CapabilityDefinition]:
    result: dict[Capability, CapabilityDefinition] = {}
    for key, value in values.items():
        level, enabled = value if isinstance(value, tuple) else (value, True)
        result[Capability(key)] = CapabilityDefinition(level, enabled)
    return MappingProxyType(result)


_MODELS: tuple[ScaleModelDefinition, ...] = (
    ScaleModelDefinition(
        "eufy T9120",
        "Eufy Smart Scale A1",
        "T9120",
        "onebyone",
        TransportMode.GATT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=SupportLevel.UPSTREAM_VALIDATED,
            battery=SupportLevel.UPSTREAM_VALIDATED,
            body_composition=(SupportLevel.EXPERIMENTAL, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9130",
        "Eufy Smart Scale C20",
        "T9130",
        "c20",
        TransportMode.ADVERTISEMENT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=SupportLevel.UPSTREAM_VALIDATED,
            heart_rate=SupportLevel.UPSTREAM_VALIDATED,
            body_composition=(SupportLevel.EXPERIMENTAL, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9140",
        "Eufy Smart Scale",
        "T9140",
        "legacy_t9140",
        TransportMode.GATT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=(SupportLevel.EXPERIMENTAL, False),
            battery=SupportLevel.UPSTREAM_VALIDATED,
            body_composition=(SupportLevel.EXPERIMENTAL, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9146",
        "Eufy Smart Scale C1",
        "T9146",
        "onebyone",
        TransportMode.ADVERTISEMENT_WITH_OPTIONAL_GATT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=(SupportLevel.UPSTREAM_VALIDATED, False),
            battery=(SupportLevel.UPSTREAM_VALIDATED, False),
            body_composition=(SupportLevel.EXPERIMENTAL, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9147",
        "Eufy Smart Scale P1",
        "T9147",
        "onebyone",
        TransportMode.ADVERTISEMENT_WITH_OPTIONAL_GATT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=(SupportLevel.UPSTREAM_VALIDATED, False),
            battery=(SupportLevel.UPSTREAM_VALIDATED, False),
            body_composition=(SupportLevel.EXPERIMENTAL, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9148",
        "Eufy Smart Scale P2",
        "T9148",
        "p2",
        TransportMode.ADVERTISEMENT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            impedance=(SupportLevel.UNSUPPORTED, False),
            body_composition=(SupportLevel.UNSUPPORTED, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9149",
        "Eufy Smart Scale P2 Pro",
        "T9149",
        "p2",
        TransportMode.ADVERTISEMENT,
        _caps(
            live_weight=SupportLevel.UPSTREAM_VALIDATED,
            final_weight=SupportLevel.UPSTREAM_VALIDATED,
            heart_rate=SupportLevel.UPSTREAM_VALIDATED,
            impedance=(SupportLevel.UNSUPPORTED, False),
            body_composition=(SupportLevel.UNSUPPORTED, False),
        ),
    ),
    ScaleModelDefinition(
        "eufy T9150",
        "Eufy Smart Scale P3",
        "T9150",
        "p3",
        TransportMode.ADVERTISEMENT,
        _caps(
            live_weight=SupportLevel.VERIFIED,
            final_weight=SupportLevel.VERIFIED,
            impedance=SupportLevel.VERIFIED,
            heart_rate=SupportLevel.VERIFIED,
            body_composition=SupportLevel.EXPERIMENTAL,
        ),
    ),
)

SUPPORTED_MODELS: Final = MappingProxyType({model.model_id: model for model in _MODELS})


def get_model(model_id: str) -> ScaleModelDefinition | None:
    return SUPPORTED_MODELS.get(model_id)


def capability_enabled(
    model: ScaleModelDefinition,
    capability: Capability,
    options: Mapping[str, object],
) -> bool:
    definition = model.capability(capability)
    if definition.level is SupportLevel.UNSUPPORTED:
        return False
    if definition.enabled_by_default:
        return True
    if capability in {
        Capability.IMPEDANCE,
        Capability.BATTERY,
    } and model.model_name in {"T9146", "T9147"}:
        return bool(options.get("extended_metrics"))
    if capability is Capability.IMPEDANCE and model.model_name == "T9140":
        return bool(options.get("experimental_impedance"))
    if capability is Capability.BODY_COMPOSITION:
        enabled = bool(options.get("experimental_cross_model_composition"))
        if model.model_name in {"T9146", "T9147"}:
            return enabled and bool(options.get("extended_metrics"))
        if model.model_name == "T9140":
            return enabled and bool(options.get("experimental_impedance"))
        return enabled
    return False
