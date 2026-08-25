from types import SimpleNamespace

from custom_components.eufy_smart_scale_ble.diagnostics import (
    RuntimeDiagnostics,
    async_get_config_entry_diagnostics,
)
from custom_components.eufy_smart_scale_ble.model_registry import SUPPORTED_MODELS
from custom_components.eufy_smart_scale_ble.protocols.base import (
    MeasurementEvent,
    MeasurementPhase,
)


async def test_diagnostics_contain_protocol_metadata_not_personal_values() -> None:
    stats = RuntimeDiagnostics()
    stats.record_advertisement({1: bytes(23)})
    stats.record_event(
        MeasurementEvent(
            MeasurementPhase.COMPLETE,
            weight_kg=64.32,
            impedance_ohm=543.2,
            heart_rate_bpm=88,
            status="complete",
        )
    )
    runtime = SimpleNamespace(model=SUPPORTED_MODELS["eufy T9150"], diagnostics=stats)
    result = await async_get_config_entry_diagnostics(
        None, SimpleNamespace(runtime_data=runtime)
    )
    text = repr(result).lower()
    assert result["model"] == "T9150"
    assert result["runtime"]["packet_lengths_seen"] == [23]
    for forbidden in (
        "64.32",
        "543.2",
        "heart_rate_bpm",
        "weight_kg",
        "impedance_ohm",
        "address",
        "raw_packet",
    ):
        assert forbidden not in text
