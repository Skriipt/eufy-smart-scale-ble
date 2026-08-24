"""Config flow for Eufy Smart Scale P3 BLE."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_MODEL
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .body_composition import (
    MAX_AGE,
    MAX_HEIGHT_CM,
    MIN_AGE,
    MIN_HEIGHT_CM,
    ProfileMode,
    Sex,
)
from .const import (
    CONF_AGE,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_SEX,
    DEFAULT_AGE,
    DEFAULT_HEIGHT_CM,
    DEFAULT_PROFILE_MODE,
    DEFAULT_SEX,
    DEVICE_NAME,
    DOMAIN,
    MODEL_ID,
)

SEX_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[value.value for value in Sex],
        translation_key=CONF_SEX,
    )
)
PROFILE_MODE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[value.value for value in ProfileMode],
        translation_key=CONF_PROFILE_MODE,
    )
)


def _profile_schema(options: dict[str, Any]) -> vol.Schema:
    """Build the editable body-composition profile schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SEX,
                default=options.get(CONF_SEX, DEFAULT_SEX),
            ): SEX_SELECTOR,
            vol.Required(
                CONF_HEIGHT_CM,
                default=options.get(CONF_HEIGHT_CM, DEFAULT_HEIGHT_CM),
            ): vol.All(int, vol.Range(min=MIN_HEIGHT_CM, max=MAX_HEIGHT_CM)),
            vol.Required(
                CONF_AGE,
                default=options.get(CONF_AGE, DEFAULT_AGE),
            ): vol.All(int, vol.Range(min=MIN_AGE, max=MAX_AGE)),
            vol.Required(
                CONF_PROFILE_MODE,
                default=options.get(CONF_PROFILE_MODE, DEFAULT_PROFILE_MODE),
            ): PROFILE_MODE_SELECTOR,
        }
    )


class EufyP3BLEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Eufy P3 BLE configuration."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: Any) -> EufyP3OptionsFlow:
        """Return the profile options flow."""
        return EufyP3OptionsFlow()

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        if discovery_info.name != MODEL_ID:
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered scale."""
        if self._discovery_info is None:
            return self.async_abort(reason="not_supported")

        if user_input is not None:
            return self.async_create_entry(
                title=DEVICE_NAME,
                data={CONF_MODEL: MODEL_ID},
            )

        self._set_confirm_only()
        placeholders = {"name": DEVICE_NAME}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=placeholders,
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow selecting a currently discovered P3 manually."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=DEVICE_NAME,
                data={CONF_MODEL: MODEL_ID},
            )

        await bluetooth.async_request_active_scan(self.hass)
        current_ids = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            if discovery_info.name != MODEL_ID:
                continue
            address = discovery_info.address
            if address in current_ids or address in self._discovered_devices:
                continue
            self._discovered_devices[address] = f"{DEVICE_NAME} ({address})"

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )


class EufyP3OptionsFlow(OptionsFlow):
    """Manage the local body-composition calculation profile."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create or edit the body-composition profile."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_profile_schema(dict(self.config_entry.options)),
        )
