"""Capability-gated sensor entity tests."""

from datetime import UTC, datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eufy_smart_scale_ble.body_composition import (
    BodyCompositionProfile,
    Sex,
)
from custom_components.eufy_smart_scale_ble.composition_manager import (
    BodyCompositionManager,
)
from custom_components.eufy_smart_scale_ble.device import EufyScaleDevice
from custom_components.eufy_smart_scale_ble.diagnostics import RuntimeDiagnostics
from custom_components.eufy_smart_scale_ble.model_registry import SUPPORTED_MODELS
from custom_components.eufy_smart_scale_ble.models import EufyScaleRuntimeData
from custom_components.eufy_smart_scale_ble.protocol_capture import ProtocolCapture
from custom_components.eufy_smart_scale_ble.protocols.base import (
    MeasurementEvent,
    MeasurementPhase,
)
from custom_components.eufy_smart_scale_ble.sensor import async_setup_entry

ADDRESS = ":".join(["02", "00", "00", "00", "00", "01"])
PROFILE = BodyCompositionProfile(sex=Sex.MALE, height_cm=180, age=35)


def runtime(model_id: str, profile: BodyCompositionProfile | None = None):
    model = SUPPORTED_MODELS[model_id]
    device = EufyScaleDevice(now=lambda: datetime(2026, 8, 24, tzinfo=UTC))
    composition = BodyCompositionManager(profile=profile)
    device.register_callback(
        lambda state: (
            composition.update_measurement(state.body_measurement)
            if state.body_measurement is not None
            else None
        )
    )
    return EufyScaleRuntimeData(
        address=ADDRESS,
        model=model,
        device=device,
        composition=composition,
        diagnostics=RuntimeDiagnostics(),
        capture=ProtocolCapture(),
    )


async def entity_keys(model_id: str, options: dict | None = None, profile=None):
    entry = MockConfigEntry(
        domain="eufy_smart_scale_ble",
        unique_id=ADDRESS,
        data={"model": model_id},
        options=options or {},
    )
    entry.runtime_data = runtime(model_id, profile)
    entities = []
    await async_setup_entry(None, entry, entities.extend)
    return {entity.entity_description.key for entity in entities}, entities


async def test_p3_preserves_full_entity_set() -> None:
    keys, _ = await entity_keys("eufy T9150", profile=PROFILE)
    assert {
        "weight",
        "real_time_weight",
        "impedance",
        "heart_rate",
        "last_measurement",
        "packet_status",
        "bmi",
        "body_fat",
        "body_fat_mass",
        "lean_body_mass",
        "muscle_mass",
        "bone_mass",
        "body_water",
        "bmr",
        "visceral_fat",
        "protein",
        "skeletal_muscle_mass",
        "subcutaneous_fat",
        "body_age",
        "body_type",
    } == keys


async def test_p2_is_weight_only() -> None:
    keys, _ = await entity_keys("eufy T9148")
    assert keys == {"weight", "real_time_weight", "last_measurement", "packet_status"}


async def test_p2_pro_adds_heart_rate_but_no_impedance() -> None:
    keys, _ = await entity_keys("eufy T9149")
    assert keys == {
        "weight",
        "real_time_weight",
        "heart_rate",
        "last_measurement",
        "packet_status",
    }


async def test_c1_extended_metrics_add_impedance_and_battery() -> None:
    keys, _ = await entity_keys("eufy T9146", {"extended_metrics": True})
    assert "impedance" in keys
    assert "battery" in keys
    assert "bmi" not in keys


async def test_c20_experimental_composition_is_opt_in() -> None:
    options = {"experimental_cross_model_composition": True}
    keys, entities = await entity_keys("eufy T9130", options, PROFILE)
    assert "bmi" in keys
    runtime_data = entities[0]._data
    runtime_data.device.process_event(
        MeasurementEvent(MeasurementPhase.LIVE, weight_kg=78.4, status="live")
    )
    runtime_data.device.process_event(
        MeasurementEvent(
            MeasurementPhase.LOCKED,
            weight_kg=78.45,
            impedance_ohm=510.0,
            status="locked",
        )
    )
    bmi = next(e for e in entities if e.entity_description.key == "bmi")
    assert bmi.native_value == 24.1
    assert bmi.extra_state_attributes["algorithm_basis_model"] == "T9150"
    assert bmi.extra_state_attributes["model_support"] == "experimental"
