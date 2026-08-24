"""Tests for Eufy P3 BLE sensor entities."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.eufy_p3_ble.const import DOMAIN
from custom_components.eufy_p3_ble.device import EufyP3Device
from custom_components.eufy_p3_ble.models import EufyP3RuntimeData
from custom_components.eufy_p3_ble.sensor import async_setup_entry
from tests.common import MockConfigEntry
from tests.fixtures.t9150_packets import HEART_RATE_82_75, LIVE_82_71

ADDRESS = "11:22:33:44:55:66"


async def test_creates_all_six_entities(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.runtime_data = EufyP3RuntimeData(ADDRESS, EufyP3Device())
    entities = []
    await async_setup_entry(hass, entry, entities.extend)
    assert len(entities) == 6
    assert {entity.entity_description.key for entity in entities} == {
        "weight",
        "real_time_weight",
        "impedance",
        "heart_rate",
        "last_measurement",
        "packet_status",
    }


async def test_entity_metadata() -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.runtime_data = EufyP3RuntimeData(ADDRESS, EufyP3Device())
    entities = []
    await async_setup_entry(None, entry, entities.extend)
    by_key = {entity.entity_description.key: entity for entity in entities}
    assert by_key["weight"].device_class is SensorDeviceClass.WEIGHT
    assert by_key["last_measurement"].device_class is SensorDeviceClass.TIMESTAMP
    assert by_key["packet_status"].device_class is SensorDeviceClass.ENUM
    assert by_key["packet_status"].entity_category is EntityCategory.DIAGNOSTIC
    assert by_key["weight"].unique_id.endswith("_weight")


async def test_entities_follow_device_updates() -> None:
    device = EufyP3Device(now=lambda: datetime(2026, 8, 24, tzinfo=UTC))
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.runtime_data = EufyP3RuntimeData(ADDRESS, device)
    entities = []
    await async_setup_entry(None, entry, entities.extend)
    by_key = {entity.entity_description.key: entity for entity in entities}

    for entity in entities:
        entity.async_write_ha_state = lambda: None
        entity._subscribe_for_test()

    device.process({1: LIVE_82_71})
    assert by_key["real_time_weight"].native_value == 82.71
    assert by_key["weight"].native_value is None

    device.process({1: HEART_RATE_82_75})
    assert by_key["weight"].native_value == 82.75
    assert by_key["impedance"].native_value == 435.0
    assert by_key["heart_rate"].native_value == 72
    assert by_key["last_measurement"].native_value == datetime(2026, 8, 24, tzinfo=UTC)
    assert by_key["packet_status"].native_value == "complete"
    assert by_key["packet_status"].extra_state_attributes["status_hex"] == "0xE5"


async def test_restored_sensor_uses_last_native_value(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.runtime_data = EufyP3RuntimeData(ADDRESS, EufyP3Device())
    entities = []
    await async_setup_entry(hass, entry, entities.extend)
    weight = next(e for e in entities if e.entity_description.key == "weight")
    weight.hass = hass
    weight.entity_id = "sensor.test_weight"
    restored = type("Stored", (), {"native_value": 81.2})()
    with (
        patch.object(
            weight,
            "async_get_last_sensor_data",
            new=AsyncMock(return_value=restored),
        ),
        patch.object(weight, "async_on_remove"),
    ):
        await weight.async_added_to_hass()
    assert weight.native_value == 81.2
