"""Eufy Smart Scale P3 BLE integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .body_composition import BodyMeasurement, profile_from_mapping
from .composition_manager import BodyCompositionManager
from .device import EufyP3Device
from .models import EufyP3RuntimeData, ScaleState
from .storage import async_load_measurement, async_save_measurement

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one Eufy P3 from a config entry."""
    from homeassistant.components import bluetooth as ha_bluetooth
    from homeassistant.components.bluetooth.match import (
        ADDRESS,
        BluetoothCallbackMatcher,
    )
    from homeassistant.const import Platform
    from homeassistant.util import dt as dt_util

    address = entry.unique_id
    if address is None:
        _LOGGER.error("Eufy P3 config entry has no Bluetooth address")
        return False

    restored_measurement: BodyMeasurement | None = None
    try:
        restored_measurement = await async_load_measurement(hass, entry.entry_id)
    except Exception as err:  # Defensive boundary around persistent user data.
        _LOGGER.warning("Unable to restore the latest Eufy P3 measurement: %s", err)

    composition = BodyCompositionManager(
        profile=profile_from_mapping(entry.options),
        measurement=restored_measurement,
    )
    device = EufyP3Device(
        now=dt_util.utcnow,
        restored_measurement=restored_measurement,
    )
    entry.runtime_data = EufyP3RuntimeData(
        address=address,
        device=device,
        composition=composition,
    )

    async def _async_persist(measurement: BodyMeasurement) -> None:
        try:
            await async_save_measurement(hass, entry.entry_id, measurement)
        except Exception as err:  # Storage failure must not break BLE processing.
            _LOGGER.warning("Unable to store the latest Eufy P3 measurement: %s", err)

    def _async_update_composition(state: ScaleState) -> None:
        measurement = state.body_measurement
        if measurement is None or not composition.update_measurement(measurement):
            return
        hass.async_create_task(_async_persist(measurement))

    entry.async_on_unload(device.register_callback(_async_update_composition))

    logged_errors: set[tuple[type[BaseException], str]] = set()

    def _async_update_ble(service_info: Any, _change: Any) -> None:
        """Process a Bluetooth advertisement without allowing it to escape."""
        try:
            device.process(service_info.manufacturer_data)
        except Exception as err:  # Defensive boundary for untrusted BLE input.
            signature = (type(err), str(err))
            if signature not in logged_errors:
                logged_errors.add(signature)
                _LOGGER.warning(
                    "Unable to process an Eufy P3 Bluetooth advertisement: %s", err
                )

    entry.async_on_unload(
        ha_bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            BluetoothCallbackMatcher({ADDRESS: address}),
            ha_bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    if service_info := ha_bluetooth.async_last_service_info(hass, address, False):
        _async_update_ble(service_info, None)

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration after profile options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one Eufy P3 config entry."""
    from homeassistant.const import Platform

    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
