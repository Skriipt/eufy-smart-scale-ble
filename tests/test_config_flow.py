"""Tests for Eufy P3 BLE config and profile options flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from custom_components.eufy_p3_ble.const import (
    CONF_AGE,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_SEX,
    DOMAIN,
    MODEL_ID,
)
from tests.common import MockConfigEntry

ADDRESS = "11:22:33:44:55:66"
SERVICE_INFO = BluetoothServiceInfo(
    name=MODEL_ID,
    address=ADDRESS,
    rssi=-55,
    manufacturer_data={},
    service_data={},
    service_uuids=[],
    source="local",
)
NOT_SUPPORTED = BluetoothServiceInfo(
    name="other scale",
    address="AA:BB:CC:DD:EE:FF",
    rssi=-55,
    manufacturer_data={},
    service_data={},
    service_uuids=[],
    source="local",
)
PROFILE_OPTIONS = {
    CONF_SEX: "male",
    CONF_HEIGHT_CM: 180,
    CONF_AGE: 35,
    CONF_PROFILE_MODE: "normal",
}


async def test_bluetooth_discovery(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch("custom_components.eufy_p3_ble.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eufy Smart Scale P3"
    assert result["data"] == {"model": MODEL_ID}
    assert result["result"].unique_id == ADDRESS


async def test_unsupported_bluetooth_device_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=NOT_SUPPORTED,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_duplicate_discovery_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={"model": MODEL_ID})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_flow_lists_discovered_scale(hass: HomeAssistant) -> None:
    with (
        patch(
            "custom_components.eufy_p3_ble.config_flow.async_discovered_service_info",
            return_value=[SERVICE_INFO, NOT_SUPPORTED],
        ),
        patch(
            "custom_components.eufy_p3_ble.config_flow.bluetooth.async_request_active_scan"
        ) as request_scan,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    request_scan.assert_awaited_once_with(hass)

    with patch("custom_components.eufy_p3_ble.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"address": ADDRESS}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == ADDRESS


async def test_manual_flow_without_scale_aborts(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.eufy_p3_ble.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_profile_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={"model": MODEL_ID},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=PROFILE_OPTIONS
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == PROFILE_OPTIONS
    assert entry.options == PROFILE_OPTIONS


async def test_profile_options_flow_uses_saved_values(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={"model": MODEL_ID},
        options=PROFILE_OPTIONS,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    values = result["data_schema"]({})

    assert values == PROFILE_OPTIONS
