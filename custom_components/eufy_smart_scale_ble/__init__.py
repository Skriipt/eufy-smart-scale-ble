"""Eufy Smart Scale BLE integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .bluetooth import create_advertisement_parser
from .body_composition import BodyMeasurement, profile_from_mapping
from .composition_manager import BodyCompositionManager
from .const import (
    CONF_EXPERIMENTAL_IMPEDANCE,
    CONF_EXTENDED_METRICS,
    CONF_PROTOCOL_CAPTURE,
)
from .device import EufyScaleDevice
from .diagnostics import RuntimeDiagnostics
from .gatt import EufyGattSession
from .model_registry import (
    Capability,
    TransportMode,
    capability_enabled,
    get_model,
)
from .models import EufyScaleRuntimeData, ScaleState
from .protocol_capture import ProtocolCapture
from .storage import async_load_measurement, async_save_measurement

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one Eufy scale."""
    from homeassistant.components import bluetooth as ha_bluetooth
    from homeassistant.components.bluetooth.match import (
        ADDRESS,
        BluetoothCallbackMatcher,
    )
    from homeassistant.const import CONF_MODEL, Platform
    from homeassistant.util import dt as dt_util

    address = entry.unique_id
    model_id = entry.data.get(CONF_MODEL)
    model = get_model(model_id) if isinstance(model_id, str) else None
    if address is None or model is None:
        _LOGGER.error("Eufy scale config entry has no valid Bluetooth address/model")
        return False

    restored_measurement: BodyMeasurement | None = None
    if model.capability(Capability.BODY_COMPOSITION).level.value != "unsupported":
        try:
            restored_measurement = await async_load_measurement(hass, entry.entry_id)
        except Exception as err:
            _LOGGER.warning(
                "Unable to restore the latest Eufy scale measurement: %s", err
            )

    composition_enabled = capability_enabled(
        model, Capability.BODY_COMPOSITION, entry.options
    )
    composition = BodyCompositionManager(
        profile=profile_from_mapping(entry.options) if composition_enabled else None,
        measurement=restored_measurement,
    )
    device = EufyScaleDevice(
        now=dt_util.utcnow,
        restored_measurement=restored_measurement,
    )
    diagnostics = RuntimeDiagnostics()
    capture = ProtocolCapture(enabled=bool(entry.options.get(CONF_PROTOCOL_CAPTURE)))
    runtime = EufyScaleRuntimeData(
        address=address,
        model=model,
        device=device,
        composition=composition,
        diagnostics=diagnostics,
        capture=capture,
    )
    entry.runtime_data = runtime

    async def _async_persist(measurement: BodyMeasurement) -> None:
        try:
            await async_save_measurement(hass, entry.entry_id, measurement)
        except Exception as err:
            _LOGGER.warning(
                "Unable to store the latest Eufy scale measurement: %s", err
            )

    def _update_composition(state: ScaleState) -> None:
        measurement = state.body_measurement
        if measurement is None or not composition.update_measurement(measurement):
            return
        hass.async_create_task(_async_persist(measurement))

    entry.async_on_unload(device.register_callback(_update_composition))

    def _process_event(event: Any) -> None:
        diagnostics.record_event(event)
        device.process_event(event)

    parser = create_advertisement_parser(model)
    needs_gatt = model.transport is TransportMode.GATT or (
        model.transport is TransportMode.ADVERTISEMENT_WITH_OPTIONAL_GATT
        and bool(entry.options.get(CONF_EXTENDED_METRICS))
    )
    if needs_gatt:
        runtime.gatt = EufyGattSession(
            hass,
            address,
            model,
            _process_event,
            capture=capture,
            allow_experimental_impedance=bool(
                entry.options.get(CONF_EXPERIMENTAL_IMPEDANCE)
            ),
            on_connect=lambda: setattr(
                diagnostics, "gatt_connections", diagnostics.gatt_connections + 1
            ),
            on_failure=lambda: setattr(
                diagnostics, "gatt_failures", diagnostics.gatt_failures + 1
            ),
        )
        entry.async_on_unload(
            lambda: (
                hass.async_create_task(runtime.gatt.async_stop())
                if runtime.gatt is not None
                else None
            )
        )

    logged_errors: set[tuple[type[BaseException], str]] = set()

    def _update_ble(service_info: Any, _change: Any) -> None:
        try:
            manufacturer_data = service_info.manufacturer_data
            diagnostics.record_advertisement(manufacturer_data)
            for raw in manufacturer_data.values():
                capture.add(raw)
            if parser is not None:
                for event in parser.parse(manufacturer_data):
                    _process_event(event)
            if runtime.gatt is not None:
                hass.async_create_task(runtime.gatt.async_ensure_connected())
        except Exception as err:
            signature = (type(err), str(err))
            if signature not in logged_errors:
                logged_errors.add(signature)
                _LOGGER.warning("Unable to process Eufy scale Bluetooth data: %s", err)

    entry.async_on_unload(
        ha_bluetooth.async_register_callback(
            hass,
            _update_ble,
            BluetoothCallbackMatcher({ADDRESS: address}),
            ha_bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    if service_info := ha_bluetooth.async_last_service_info(hass, address, False):
        _update_ble(service_info, None)

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import Platform

    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
