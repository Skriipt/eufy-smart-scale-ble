"""Tests for Eufy P3 BLE sensor entities."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.eufy_p3_ble.body_composition import (
    ALGORITHM_ID,
    ALGORITHM_STATUS,
    BodyCompositionProfile,
    Sex,
)
from custom_components.eufy_p3_ble.composition_manager import BodyCompositionManager
from custom_components.eufy_p3_ble.const import DOMAIN
from custom_components.eufy_p3_ble.device import EufyP3Device
from custom_components.eufy_p3_ble.models import EufyP3RuntimeData, ScaleState
from custom_components.eufy_p3_ble.sensor import async_setup_entry
from tests.common import MockConfigEntry
from tests.fixtures.t9150_packets import LIVE_SAMPLE, make_packet

ADDRESS = "11:22:33:44:55:66"
PROFILE = BodyCompositionProfile(sex=Sex.MALE, height_cm=180, age=35)
RAW_KEYS = {
    "weight",
    "real_time_weight",
    "impedance",
    "heart_rate",
    "last_measurement",
    "packet_status",
}
CALCULATED_KEYS = {
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
}


def _runtime(profile: BodyCompositionProfile | None = None) -> EufyP3RuntimeData:
    device = EufyP3Device(now=lambda: datetime(2026, 8, 24, tzinfo=UTC))
    composition = BodyCompositionManager(profile=profile)

    def update_composition(state: ScaleState) -> None:
        if state.body_measurement is not None:
            composition.update_measurement(state.body_measurement)

    device.register_callback(update_composition)
    return EufyP3RuntimeData(ADDRESS, device, composition)


async def _entities(
    hass: HomeAssistant | None,
    profile: BodyCompositionProfile | None = None,
):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.runtime_data = _runtime(profile)
    entities = []
    await async_setup_entry(hass, entry, entities.extend)
    return entry, entities


async def test_creates_raw_and_calculated_entities(hass: HomeAssistant) -> None:
    _, entities = await _entities(hass)

    assert len(entities) == 20
    assert {entity.entity_description.key for entity in entities} == (
        RAW_KEYS | CALCULATED_KEYS
    )


async def test_entity_metadata() -> None:
    _, entities = await _entities(None)
    by_key = {entity.entity_description.key: entity for entity in entities}

    assert by_key["weight"].device_class is SensorDeviceClass.WEIGHT
    assert by_key["last_measurement"].device_class is SensorDeviceClass.TIMESTAMP
    assert by_key["packet_status"].device_class is SensorDeviceClass.ENUM
    assert by_key["packet_status"].entity_category is EntityCategory.DIAGNOSTIC
    assert by_key["body_type"].device_class is SensorDeviceClass.ENUM
    assert "obese" in by_key["body_type"].options
    assert by_key["weight"].unique_id.endswith("_weight")
    assert by_key["body_fat"].unique_id.endswith("_body_fat")


async def test_calculated_entities_are_unavailable_without_profile() -> None:
    _, entities = await _entities(None)
    bmi = next(entity for entity in entities if entity.entity_description.key == "bmi")

    assert not bmi.available
    assert bmi.native_value is None


async def test_entities_follow_complete_measurement() -> None:
    entry, entities = await _entities(None, PROFILE)
    by_key = {entity.entity_description.key: entity for entity in entities}

    for entity in entities:
        entity.async_write_ha_state = lambda: None
        entity._subscribe_for_test()

    entry.runtime_data.device.process({1: LIVE_SAMPLE})
    assert by_key["real_time_weight"].native_value == 72.31
    assert by_key["weight"].native_value is None
    assert by_key["bmi"].native_value is None

    complete = make_packet(
        sequence=0x58,
        status=0xE5,
        weight_kg=78.45,
        heart_rate=72,
        impedance_ohm=510.0,
    )
    entry.runtime_data.device.process({1: complete})

    assert by_key["weight"].native_value == 78.45
    assert by_key["impedance"].native_value == 510.0
    assert by_key["heart_rate"].native_value == 72
    assert by_key["bmi"].native_value == 24.1
    assert by_key["body_fat"].native_value == 22.8
    assert by_key["body_fat_mass"].native_value == 17.8
    assert by_key["lean_body_mass"].native_value == 60.7
    assert by_key["muscle_mass"].native_value == 57.6
    assert by_key["bone_mass"].native_value == 3.0
    assert by_key["visceral_fat"].native_value == 11
    assert by_key["body_age"].native_value == 36
    assert by_key["body_type"].native_value == "average"

    attributes = by_key["body_fat"].extra_state_attributes
    assert attributes["source"] == "locally_calculated"
    assert attributes["algorithm"] == ALGORITHM_ID
    assert attributes["algorithm_status"] == ALGORITHM_STATUS
    assert attributes["input_weight_kg"] == 78.45
    assert attributes["input_impedance_ohm"] == 510.0
    assert attributes["profile_height_cm"] == 180
    assert attributes["profile_age"] == 35


async def test_restored_raw_sensor_uses_last_native_value(
    hass: HomeAssistant,
) -> None:
    _, entities = await _entities(hass)
    weight = next(e for e in entities if e.entity_description.key == "weight")
    weight.hass = hass
    weight.entity_id = "sensor.test_weight"
    restored = type("Stored", (), {"native_value": 71.2})()
    with (
        patch.object(
            weight,
            "async_get_last_sensor_data",
            new=AsyncMock(return_value=restored),
        ),
        patch.object(weight, "async_on_remove"),
    ):
        await weight.async_added_to_hass()
    assert weight.native_value == 71.2
