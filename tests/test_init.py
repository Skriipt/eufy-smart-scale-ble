"""Runtime setup coverage for generic Eufy scales."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.components import bluetooth
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

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
from tests.common import MockConfigEntry
from tests.fixtures.t9150_packets import FINAL_SAMPLE, LIVE_SAMPLE

ADDRESS = ":".join(("02", "00", "00", "00", "00", "01"))
PROFILE = {CONF_SEX: "male", CONF_HEIGHT_CM: 180, CONF_AGE: 35, CONF_PROFILE_MODE: "normal"}
RESTORED = BodyMeasurement(71.8, 505.0, datetime(2026, 8, 23, 8, 0, tzinfo=UTC))


def service_info(model: str, data: dict[int, bytes]) -> BluetoothServiceInfo:
    return BluetoothServiceInfo(
        name=model,
        address=ADDRESS,
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
            return_value=service_info(
                "eufy T9150", {1: LIVE_SAMPLE, 2: FINAL_SAMPLE}
            ),
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
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: "eufy T9150"})
    reload_entry = AsyncMock()
    with patch.object(hass.config_entries, "async_reload", new=reload_entry):
        await _async_reload_entry(hass, entry)
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_unload_forwards_to_sensor_platform(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: "eufy T9150"})
    unload = AsyncMock(return_value=True)
    with patch.object(hass.config_entries, "async_unload_platforms", unload):
        assert await async_unload_entry(hass, entry)
