"""Config-flow coverage for all supported scale model IDs."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from custom_components.eufy_smart_scale_ble.const import (
    CONF_AGE,
    CONF_EXPERIMENTAL_COMPOSITION,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_SEX,
    DOMAIN,
)
from custom_components.eufy_smart_scale_ble.model_registry import SUPPORTED_MODELS
from tests.common import MockConfigEntry

ADDRESS = ":".join(("02", "00", "00", "00", "00", "01"))


def info(model: str, address: str = ADDRESS) -> BluetoothServiceInfo:
    return BluetoothServiceInfo(
        name=model,
        address=address,
        rssi=-55,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        source="local",
    )


@pytest.mark.parametrize("model_id", SUPPORTED_MODELS)
async def test_bluetooth_discovery_supports_all_models(
    hass: HomeAssistant, model_id: str
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info(model_id),
    )
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.eufy_smart_scale_ble.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"model": model_id}
    assert result["title"] == SUPPORTED_MODELS[model_id].display_name


async def test_unknown_scale_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info("eufy T9999"),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_manual_flow_lists_supported_models_only(hass: HomeAssistant) -> None:
    supported = info("eufy T9149")
    unsupported = info("other scale", ":".join(("02", "00", "00", "00", "00", "02")))
    with (
        patch(
            "custom_components.eufy_smart_scale_ble.config_flow.async_discovered_service_info",
            return_value=[supported, unsupported],
        ),
        patch(
            "custom_components.eufy_smart_scale_ble.config_flow.bluetooth.async_request_active_scan"
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.eufy_smart_scale_ble.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"address": ADDRESS}
        )
    assert result["data"] == {"model": "eufy T9149"}


async def test_p3_options_keep_profile_without_experimental_toggle(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={"model": "eufy T9150"},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    values = result["data_schema"]({})
    assert CONF_SEX in values
    assert CONF_EXPERIMENTAL_COMPOSITION not in values


async def test_c20_options_offer_experimental_composition(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={"model": "eufy T9130"},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    values = result["data_schema"]({})
    assert values[CONF_EXPERIMENTAL_COMPOSITION] is False
    user_input = {
        **values,
        CONF_EXPERIMENTAL_COMPOSITION: True,
        CONF_SEX: "male",
        CONF_HEIGHT_CM: 180,
        CONF_AGE: 35,
        CONF_PROFILE_MODE: "normal",
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_existing_entry_model_cannot_change_via_new_discovery(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={"model": "eufy T9150"},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=info("eufy T9130"),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["model"] == "eufy T9150"
