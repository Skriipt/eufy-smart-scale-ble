"""Runtime setup coverage for generic Eufy scales."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components import bluetooth
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eufy_smart_scale_ble import (
    _async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.eufy_smart_scale_ble.body_composition import BodyMeasurement
from custom_components.eufy_smart_scale_ble.const import (
    CONF_AGE,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_SEX,
    DOMAIN,
)
from custom_components.eufy_smart_scale_ble.model_registry import TransportMode
from tests.fixtures.t9150_packets import FINAL_SAMPLE, LIVE_SAMPLE

ADDRESS = ":".join(("02", "00", "00", "00", "00", "01"))
PROFILE = {
    CONF_SEX: "male",
    CONF_HEIGHT_CM: 180,
    CONF_AGE: 35,
    CONF_PROFILE_MODE: "normal",
}
RESTORED = BodyMeasurement(71.8, 505.0, datetime(2026, 8, 23, 8, 0, tzinfo=UTC))


def service_info(
    model: str, data: dict[int, bytes], *, address: str = ADDRESS
) -> BluetoothServiceInfo:
    return BluetoothServiceInfo(
        name=model,
        address=address,
        rssi=-55,
        manufacturer_data=data,
        service_data={},
        service_uuids=[],
        source="local",
    )


async def test_p3_setup_processes_cached_advertisement(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: "eufy T9150"},
        options=PROFILE,
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.eufy_smart_scale_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            bluetooth,
            "async_last_service_info",
            return_value=service_info("", {1: LIVE_SAMPLE, 2: FINAL_SAMPLE}),
        ),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.device.state.weight_kg == 72.35
    assert entry.runtime_data.model.model_name == "T9150"
    assert entry.runtime_data.gatt is None


async def test_runtime_ignores_cached_advertisement_with_conflicting_identity(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: "eufy T9150"},
        options=PROFILE,
    )
    entry.add_to_hass(hass)
    register = Mock(return_value=lambda: None)
    with (
        patch(
            "custom_components.eufy_smart_scale_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            bluetooth,
            "async_last_service_info",
            return_value=service_info("eufy T9149", {1: FINAL_SAMPLE}),
        ),
        patch.object(bluetooth, "async_register_callback", new=register),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.device.state.weight_kg is None
    assert register.call_args.args[2] == {"address": ADDRESS, "connectable": False}


async def test_p3_restores_valid_composition_measurement(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: "eufy T9150"},
        options=PROFILE,
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.eufy_smart_scale_ble.async_load_measurement",
            new=AsyncMock(return_value=RESTORED),
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.device.state.body_measurement == RESTORED
    assert entry.runtime_data.composition.result is not None


async def test_a1_creates_gatt_session_but_does_not_connect_while_sleeping(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: "eufy T9120"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.eufy_smart_scale_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.model.transport is TransportMode.GATT
    assert entry.runtime_data.gatt is not None


async def test_options_update_reloads_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: "eufy T9150"}
    )
    reload_entry = AsyncMock()
    with patch.object(hass.config_entries, "async_reload", new=reload_entry):
        await _async_reload_entry(hass, entry)
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_unload_forwards_to_sensor_platform(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: "eufy T9150"}
    )
    unload = AsyncMock(return_value=True)
    with patch.object(hass.config_entries, "async_unload_platforms", unload):
        assert await async_unload_entry(hass, entry)


@pytest.fixture
def setup_runtime(hass, monkeypatch):
    monkeypatch.setattr(
        "custom_components.eufy_smart_scale_ble.async_load_measurement",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(bluetooth, "async_last_service_info", Mock(return_value=None))
    register = Mock(return_value=Mock())
    monkeypatch.setattr(bluetooth, "async_register_callback", register)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())

    async def setup(model="eufy T9150", options=None):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=ADDRESS,
            data={CONF_MODEL: model},
            options=options or PROFILE,
        )
        entry.add_to_hass(hass)
        assert await async_setup_entry(hass, entry)
        return entry, register.call_args.args[1], register.call_args.args[2]

    return setup


@pytest.mark.parametrize(
    "model", ["eufy T9150", "eufy T9130", "eufy T9146", "eufy T9149"]
)
async def test_passive_proxy_matches_runtime_subscription(setup_runtime, model) -> None:
    from homeassistant.components.bluetooth.match import ble_device_matches

    _, _, matcher = await setup_runtime(model)
    assert ble_device_matches(matcher, SimpleNamespace(connectable=False))


async def test_persistence_is_ordered_and_unload_waits_for_it(
    hass, monkeypatch, setup_runtime
):
    from custom_components.eufy_smart_scale_ble.protocols.base import (
        MeasurementEvent,
        MeasurementPhase,
    )

    release = asyncio.Event()
    started = []
    saved = []

    async def save(_hass, _entry_id, measurement):
        started.append(measurement.weight_kg)
        if measurement.weight_kg == 60.0:
            await release.wait()
        saved.append(measurement.weight_kg)

    monkeypatch.setattr(
        "custom_components.eufy_smart_scale_ble.async_save_measurement", save
    )
    entry, _, _ = await setup_runtime()
    device = entry.runtime_data.device
    for weight in (60.0, 80.0):
        device.process_event(MeasurementEvent(MeasurementPhase.LIVE, weight_kg=weight))
        device.process_event(
            MeasurementEvent(
                MeasurementPhase.LOCKED, weight_kg=weight, impedance_ohm=500.0
            )
        )
    unloading = asyncio.create_task(entry._async_process_on_unload(hass))
    try:
        await asyncio.sleep(0)
        assert started == [60.0]
        assert not unloading.done()
    finally:
        release.set()
        await unloading
    assert saved == [60.0, 80.0]


async def test_unload_clears_capture(hass, setup_runtime):
    entry, _, _ = await setup_runtime(options={"protocol_capture": True})
    capture = entry.runtime_data.capture
    capture.add(b"synthetic-private-frame")
    assert capture.frames
    await entry._async_process_on_unload(hass)
    assert capture.frames == ()


async def test_runtime_exception_does_not_log_private_details(
    setup_runtime, monkeypatch, caplog
):
    parser = Mock()
    parser.parse.side_effect = ValueError("synthetic-private-payload")
    monkeypatch.setattr(
        "custom_components.eufy_smart_scale_ble.create_advertisement_parser",
        lambda _model: parser,
    )
    _, callback, _ = await setup_runtime()
    for _ in range(2):
        callback(service_info("eufy T9150", {}), None)
    assert "synthetic-private-payload" not in caplog.text
    assert (
        caplog.text.count("Unable to process Eufy scale Bluetooth data: ValueError")
        == 1
    )


async def test_shutdown_stops_gatt(hass, setup_runtime):
    from homeassistant.const import EVENT_HOMEASSISTANT_STOP

    entry, _, _ = await setup_runtime("eufy T9120")
    stop = AsyncMock()
    entry.runtime_data.gatt.async_stop = stop
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    stop.assert_awaited_once()
