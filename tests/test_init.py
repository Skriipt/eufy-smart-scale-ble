"""Tests for Eufy P3 BLE runtime setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.components import bluetooth
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from custom_components.eufy_p3_ble import async_setup_entry, async_unload_entry
from custom_components.eufy_p3_ble.const import DOMAIN, MODEL_ID
from custom_components.eufy_p3_ble.models import PacketStatus
from tests.common import MockConfigEntry
from tests.fixtures.t9150_packets import FINAL_82_75, LIVE_82_71

ADDRESS = "11:22:33:44:55:66"


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
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(hass.config_entries, "async_forward_entry_setups", forward),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.address == ADDRESS
    assert entry.runtime_data.device.state.weight_kg is None
    forward.assert_awaited_once()


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
        patch.object(bluetooth, "async_last_service_info", return_value=None),
        patch.object(bluetooth, "async_register_callback", side_effect=register),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)

    callbacks[0](
        service_info({53075: LIVE_82_71, 53085: FINAL_82_75}),
        bluetooth.BluetoothChange.ADVERTISEMENT,
    )
    state = entry.runtime_data.device.state
    assert state.packet_status is PacketStatus.LOCKED
    assert state.weight_kg == 82.75


async def test_cached_service_info_is_processed_during_setup(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    entry.add_to_hass(hass)
    with (
        patch.object(
            bluetooth,
            "async_last_service_info",
            return_value=service_info({53085: FINAL_82_75}),
        ),
        patch.object(bluetooth, "async_register_callback", return_value=lambda: None),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.device.state.weight_kg == 82.75


async def test_unload_forwards_to_sensor_platform(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={CONF_MODEL: MODEL_ID}
    )
    unload = AsyncMock(return_value=True)
    with patch.object(hass.config_entries, "async_unload_platforms", unload):
        assert await async_unload_entry(hass, entry)
    unload.assert_awaited_once()
