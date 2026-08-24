"""Eufy Smart Scale P3 BLE integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .device import EufyP3Device
from .models import EufyP3RuntimeData

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

    device = EufyP3Device(now=dt_util.utcnow)
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

    if service_info := ha_bluetooth.async_last_service_info(hass, address, False):
        _async_update_ble(service_info, None)

    entry.runtime_data = EufyP3RuntimeData(address=address, device=device)
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one Eufy P3 config entry."""
    from homeassistant.const import Platform

    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
