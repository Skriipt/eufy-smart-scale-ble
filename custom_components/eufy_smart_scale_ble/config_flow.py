"""Config and options flows for Eufy Smart Scale BLE."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
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
    CONF_EXPERIMENTAL_COMPOSITION,
    CONF_EXPERIMENTAL_IMPEDANCE,
    CONF_EXTENDED_METRICS,
    CONF_HEIGHT_CM,
    CONF_PROFILE_MODE,
    CONF_PROTOCOL_CAPTURE,
    CONF_SEX,
    DEFAULT_AGE,
    DEFAULT_HEIGHT_CM,
    DEFAULT_PROFILE_MODE,
    DEFAULT_SEX,
    DOMAIN,
)
from .model_registry import Capability, SupportLevel, get_model

SEX_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=[value.value for value in Sex], translation_key=CONF_SEX)
)
PROFILE_MODE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[value.value for value in ProfileMode], translation_key=CONF_PROFILE_MODE
    )
)


def _options_schema(model_id: str, options: dict[str, Any]) -> vol.Schema:
    model = get_model(model_id)
    fields: dict[Any, Any] = {
        vol.Optional(
            CONF_PROTOCOL_CAPTURE,
            default=bool(options.get(CONF_PROTOCOL_CAPTURE, False)),
        ): bool,
    }
    if model is None:
        return vol.Schema(fields)
    if model.model_name in {"T9146", "T9147"}:
        fields[
            vol.Optional(
                CONF_EXTENDED_METRICS,
                default=bool(options.get(CONF_EXTENDED_METRICS, False)),
            )
        ] = bool
    if model.model_name == "T9140":
        fields[
            vol.Optional(
                CONF_EXPERIMENTAL_IMPEDANCE,
                default=bool(options.get(CONF_EXPERIMENTAL_IMPEDANCE, False)),
            )
        ] = bool
    composition = model.capability(Capability.BODY_COMPOSITION)
    if composition.level is not SupportLevel.UNSUPPORTED:
        if not composition.enabled_by_default:
            fields[
                vol.Optional(
                    CONF_EXPERIMENTAL_COMPOSITION,
                    default=bool(options.get(CONF_EXPERIMENTAL_COMPOSITION, False)),
                )
            ] = bool
        fields.update(
            {
                vol.Required(
                    CONF_SEX, default=options.get(CONF_SEX, DEFAULT_SEX)
                ): SEX_SELECTOR,
                vol.Required(
                    CONF_HEIGHT_CM,
                    default=options.get(CONF_HEIGHT_CM, DEFAULT_HEIGHT_CM),
                ): vol.All(int, vol.Range(min=MIN_HEIGHT_CM, max=MAX_HEIGHT_CM)),
                vol.Required(
                    CONF_AGE, default=options.get(CONF_AGE, DEFAULT_AGE)
                ): vol.All(int, vol.Range(min=MIN_AGE, max=MAX_AGE)),
                vol.Required(
                    CONF_PROFILE_MODE,
                    default=options.get(CONF_PROFILE_MODE, DEFAULT_PROFILE_MODE),
                ): PROFILE_MODE_SELECTOR,
            }
        )
    return vol.Schema(fields)


class EufySmartScaleBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovery_model: str | None = None
        self._discovered_devices: dict[str, str] = {}
        self._discovered_models: dict[str, str] = {}

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: Any) -> EufyScaleOptionsFlow:
        return EufyScaleOptionsFlow()

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        model = get_model(discovery_info.name)
        if model is None:
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self._discovery_model = model.model_id
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        model = get_model(self._discovery_model or "")
        if self._discovery_info is None or model is None:
            return self.async_abort(reason="not_supported")
        if user_input is not None:
            return self.async_create_entry(
                title=model.display_name, data={CONF_MODEL: model.model_id}
            )
        self._set_confirm_only()
        placeholders = {"name": model.display_name}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            model = get_model(self._discovered_models.get(address, ""))
            if model is None:
                return self.async_abort(reason="not_supported")
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=model.display_name, data={CONF_MODEL: model.model_id}
            )

        await bluetooth.async_request_active_scan(self.hass)
        current_ids = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            model = get_model(discovery_info.name)
            if model is None:
                continue
            address = discovery_info.address
            if address in current_ids or address in self._discovered_devices:
                continue
            self._discovered_devices[address] = f"{model.display_name} ({address})"
            self._discovered_models[address] = model.model_id
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )


class EufyScaleOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        model_id = self.config_entry.data.get(CONF_MODEL, "")
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(str(model_id), dict(self.config_entry.options)),
        )
