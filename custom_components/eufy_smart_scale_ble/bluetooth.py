"""Advertisement parser selection and dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .model_registry import ScaleModelDefinition
from .protocols.base import MeasurementEvent
from .protocols.c20 import C20AdvertisementParser
from .protocols.onebyone import OnebyoneAdvertisementParser
from .protocols.p2 import parse_p2_advertisement
from .protocols.p3 import P3AdvertisementParser


class AdvertisementParser(Protocol):
    def parse(self, manufacturer_data: Mapping[int, object]) -> tuple[MeasurementEvent, ...]: ...


class P2AdvertisementParser:
    def __init__(self, *, supports_heart_rate: bool) -> None:
        self._supports_heart_rate = supports_heart_rate

    def parse(self, manufacturer_data: Mapping[int, object]) -> tuple[MeasurementEvent, ...]:
        for raw in manufacturer_data.values():
            event = parse_p2_advertisement(raw, supports_heart_rate=self._supports_heart_rate)
            if event is not None:
                return (event,)
        return ()


def create_advertisement_parser(model: ScaleModelDefinition) -> AdvertisementParser | None:
    if model.protocol_family == "p3":
        return P3AdvertisementParser()
    if model.protocol_family == "c20":
        return C20AdvertisementParser()
    if model.protocol_family == "onebyone" and model.model_name in {"T9146", "T9147"}:
        return OnebyoneAdvertisementParser()
    if model.protocol_family == "p2":
        return P2AdvertisementParser(supports_heart_rate=model.model_name == "T9149")
    return None
