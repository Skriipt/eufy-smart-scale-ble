"""Tests for persisted complete body measurements."""

from __future__ import annotations

from datetime import UTC, datetime
from math import inf, nan
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eufy_smart_scale_ble.body_composition import BodyMeasurement
from custom_components.eufy_smart_scale_ble.storage import (
    _store,
    async_load_measurement,
    async_save_measurement,
    deserialize_measurement,
    serialize_measurement,
)

MEASUREMENT = BodyMeasurement(
    weight_kg=78.45,
    impedance_ohm=510.0,
    measured_at=datetime(2026, 8, 24, 8, 30, 15, tzinfo=UTC),
)


def test_measurement_round_trip() -> None:
    stored = serialize_measurement(MEASUREMENT)

    assert stored == {
        "weight_kg": 78.45,
        "impedance_ohm": 510.0,
        "measured_at": "2026-08-24T08:30:15+00:00",
    }
    assert deserialize_measurement(stored) == MEASUREMENT


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"weight_kg": 78.45},
        {
            "weight_kg": "78.45",
            "impedance_ohm": 510.0,
            "measured_at": "2026-08-24T08:30:15+00:00",
        },
        {
            "weight_kg": 78.45,
            "impedance_ohm": 510.0,
            "measured_at": "not-a-date",
        },
        {
            "weight_kg": 78.45,
            "impedance_ohm": 510.0,
            "measured_at": "2026-08-24T08:30:15",
        },
    ],
)
def test_invalid_stored_shape_is_ignored(value: object) -> None:
    assert deserialize_measurement(value) is None


@pytest.mark.parametrize("weight", [nan, inf, -inf, 0.0, 200.01])
def test_invalid_weight_is_ignored(weight: float) -> None:
    value = serialize_measurement(MEASUREMENT) | {"weight_kg": weight}
    assert deserialize_measurement(value) is None


@pytest.mark.parametrize("impedance", [nan, inf, -inf, 49.9, 2000.1])
def test_invalid_impedance_is_ignored(impedance: float) -> None:
    value = serialize_measurement(MEASUREMENT) | {"impedance_ohm": impedance}
    assert deserialize_measurement(value) is None


def test_serialize_requires_timezone_aware_timestamp() -> None:
    measurement = BodyMeasurement(
        weight_kg=78.45,
        impedance_ohm=510.0,
        measured_at=datetime(2026, 8, 24, 8, 30),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        serialize_measurement(measurement)


async def test_measurement_file_is_private_and_removed_with_entry(
    hass: HomeAssistant, tmp_path, hass_storage
) -> None:
    from custom_components.eufy_smart_scale_ble import async_remove_entry

    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain="eufy_smart_scale_ble", data={})
    await async_save_measurement(hass, entry.entry_id, MEASUREMENT)
    store = _store(hass, entry.entry_id)
    # HA's fixture mocks Store's async I/O. Exercise its real file writer to
    # verify permissions, then verify removal through the normal storage API.
    await hass.async_add_executor_job(store._write_prepared_data, "w", "{}")
    path = Path(store.path)
    assert (await hass.async_add_executor_job(path.stat)).st_mode & 0o777 == 0o600
    assert await async_load_measurement(hass, entry.entry_id) == MEASUREMENT
    assert store.key in hass_storage
    await async_remove_entry(hass, entry)
    assert store.key not in hass_storage
