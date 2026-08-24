"""Tests for Eufy P3 BLE runtime setup."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.components import bluetooth
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from custom_components.eufy_p3_ble import (
    _async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.eufy_p3_ble.body_composition import BodyMeasurement
from custom_components.eufy_p3_ble.const import (
    CONF_AGE,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_SEX,
    DOMAIN,
    MODEL_ID,
)
from custom_components.eufy_p3_ble.models import PacketStatus
from tests.common import MockConfigEntry
from tests.fixtures.t9150_packets import FINAL_SAMPLE, LIVE_SAMPLE, make_packet

ADDRESS = "11:22:33:44:55:66"
PROFILE_OPTIONS = {
    CONF_SEX: "male",
    CONF_HEIGHT_CM: 180,
    CONF_AGE: 35,
    CONF_PROFILE_MODE: "normal",
}
RESTORED_MEASUREMENT = BodyMeasurement(
    weight_kg=71.8,
    impedance_ohm=505.0,
    measured_at=datetime(2026, 8, 23, 8, 0, tzinfo=UTC),
)


def service_info(manufacturer_data: dict[int, bytes]) -> BluetoothServiceInfo:
    return BluetoothServiceInfo(
        name=MODEL_ID,
        address=ADDRESS,
        rssi=-55,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        source="local",
    )


async def test_setup_succeeds_while_scale_is_sleeping(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    entry.add_to_hass(hass)
    forward = AsyncMock()
    with (
        patch(
            "custom_components.eufy_p3_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(hass.config_entries, "async_forward_entry_setups", forward),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.address == ADDRESS
    assert entry.runtime_data.device.state.weight_kg is None
    assert entry.runtime_data.composition.result is None
    forward.assert_awaited_once()


async def test_setup_restores_measurement_and_calculates_profile(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: MODEL_ID},
        options=PROFILE_OPTIONS,
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.eufy_p3_ble.async_load_measurement",
            new=AsyncMock(return_value=RESTORED_MEASUREMENT),
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)

    assert entry.runtime_data.device.state.body_measurement == RESTORED_MEASUREMENT
    assert entry.runtime_data.composition.measurement == RESTORED_MEASUREMENT
    assert entry.runtime_data.composition.result is not None


async def test_registered_callback_uses_newest_manufacturer_entry(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    entry.add_to_hass(hass)
    callbacks = []

    def register(_hass, callback, _matcher, _mode):
        callbacks.append(callback)
        return lambda: None

    with (
        patch(
            "custom_components.eufy_p3_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", side_effect=register),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)

    callbacks[0](
        service_info({53075: LIVE_SAMPLE, 53085: FINAL_SAMPLE}),
        bluetooth.BluetoothChange.ADVERTISEMENT,
    )
    state = entry.runtime_data.device.state
    assert state.packet_status is PacketStatus.LOCKED
    assert state.weight_kg == 72.35


async def test_complete_measurement_is_persisted(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_MODEL: MODEL_ID},
        options=PROFILE_OPTIONS,
    )
    entry.add_to_hass(hass)
    save = AsyncMock()
    with (
        patch(
            "custom_components.eufy_p3_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.eufy_p3_ble.async_save_measurement",
            new=save,
        ),
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
        entry.runtime_data.device.process(
            {1: make_packet(sequence=1, status=0x05, weight_kg=78.45)}
        )
        entry.runtime_data.device.process(
            {
                1: make_packet(
                    sequence=2,
                    status=0x25,
                    weight_kg=78.45,
                    impedance_ohm=510.0,
                )
            }
        )
        await hass.async_block_till_done()

    save.assert_awaited_once()
    saved = save.await_args.args[2]
    assert saved.weight_kg == 78.45
    assert saved.impedance_ohm == 510.0


async def test_cached_service_info_is_processed_during_setup(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.eufy_p3_ble.async_load_measurement",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            bluetooth,
            "async_last_service_info",
            return_value=service_info({53085: FINAL_SAMPLE}),
        ),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.device.state.weight_kg == 72.35


async def test_options_update_reloads_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    reload_entry = AsyncMock()
    with patch.object(hass.config_entries, "async_reload", new=reload_entry):
        await _async_reload_entry(hass, entry)
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_unload_forwards_to_sensor_platform(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    unload = AsyncMock(return_value=True)
    with patch.object(hass.config_entries, "async_unload_platforms", unload):
        assert await async_unload_entry(hass, entry)
    unload.assert_awaited_once()
