"""Short-lived GATT transport for Eufy models that require active BLE."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from .model_registry import ScaleModelDefinition
from .protocol_capture import ProtocolCapture
from .protocols.base import MeasurementEvent, MeasurementPhase
from .protocols.legacy_t9140 import (
    NOTIFY_CANDIDATES,
    parse_t9140_frame,
    split_notifications,
)
from .protocols.onebyone import parse_onebyone_gatt

_LOGGER = logging.getLogger(__name__)
_BATTERY_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
_ONEBYONE_NOTIFY = "0000fff4-0000-1000-8000-00805f9b34fb"


class EufyGattSession:
    """Connect only while a scale is awake, then disconnect promptly."""

    def __init__(
        self,
        hass: Any,
        address: str,
        model: ScaleModelDefinition,
        on_event: Callable[[MeasurementEvent], None],
        *,
        capture: ProtocolCapture,
        allow_experimental_impedance: bool = False,
        on_connect: Callable[[], None] | None = None,
        on_failure: Callable[[], None] | None = None,
    ) -> None:
        self._hass = hass
        self._address = address
        self._model = model
        self._on_event = on_event
        self._capture = capture
        self._allow_experimental_impedance = allow_experimental_impedance
        self._on_connect = on_connect
        self._on_failure = on_failure
        self._lock = asyncio.Lock()
        self._client: Any = None
        self._disconnect_timer: asyncio.TimerHandle | None = None

    async def async_ensure_connected(self) -> None:
        if self._client is not None and self._client.is_connected:
            self._schedule_disconnect()
            return
        if self._lock.locked():
            return
        async with self._lock:
            if self._client is not None and self._client.is_connected:
                return
            try:
                await self._async_connect()
            except Exception as err:
                if self._on_failure is not None:
                    self._on_failure()
                _LOGGER.debug(
                    "GATT connection failed for %s: %s", self._model.model_name, err
                )

    async def _async_connect(self) -> None:
        from bleak_retry_connector import (
            BleakClientWithServiceCache,
            establish_connection,
        )
        from homeassistant.components import bluetooth as ha_bluetooth

        ble_device = ha_bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            return
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._model.model_name,
            self._disconnected,
            use_services_cache=True,
            ble_device_callback=lambda: (
                ha_bluetooth.async_ble_device_from_address(
                    self._hass, self._address, connectable=True
                )
                or ble_device
            ),
        )
        notify = self._resolve_notify(client.services)
        if notify is None:
            await client.disconnect()
            raise RuntimeError("required notify characteristic not found")
        self._client = client
        await client.start_notify(notify, self._notification)
        battery = client.services.get_characteristic(_BATTERY_UUID)
        if battery is not None:
            try:
                value = await client.read_gatt_char(battery)
                if len(value) == 1 and 0 <= value[0] <= 100:
                    self._on_event(
                        MeasurementEvent(
                            phase=MeasurementPhase.LIVE,
                            battery_percent=value[0],
                            status="battery",
                        )
                    )
            except Exception:
                pass
        if self._on_connect is not None:
            self._on_connect()
        self._schedule_disconnect()

    def _resolve_notify(self, services: Any) -> Any:
        if self._model.protocol_family == "onebyone":
            return services.get_characteristic(_ONEBYONE_NOTIFY)
        if self._model.protocol_family == "legacy_t9140":
            for uuid in NOTIFY_CANDIDATES:
                if characteristic := services.get_characteristic(uuid):
                    return characteristic
        return None

    def _notification(self, _sender: Any, data: bytearray) -> None:
        raw = bytes(data)
        self._capture.add(raw)
        events: list[MeasurementEvent] = []
        if self._model.protocol_family == "onebyone":
            if event := parse_onebyone_gatt(raw):
                events.append(event)
        elif self._model.protocol_family == "legacy_t9140":
            for frame in split_notifications(raw):
                if event := parse_t9140_frame(
                    frame, allow_impedance=self._allow_experimental_impedance
                ):
                    events.append(event)
        for event in events:
            self._on_event(event)
            if event.phase.value in {"locked", "complete"}:
                self._schedule_disconnect(delay=5)

    def _schedule_disconnect(self, delay: int = 30) -> None:
        if self._disconnect_timer is not None:
            self._disconnect_timer.cancel()
        self._disconnect_timer = asyncio.get_running_loop().call_later(
            delay, lambda: self._hass.async_create_task(self.async_stop())
        )

    def _disconnected(self, _client: Any) -> None:
        self._client = None

    async def async_stop(self) -> None:
        if self._disconnect_timer is not None:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            await client.disconnect()
