"""Short-lived GATT transport for Eufy models that require active BLE."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
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
_CONNECT_DEBOUNCE_SECONDS = 5
_CONNECT_TIMEOUT_SECONDS = 30
_DISCONNECT_TIMEOUT_SECONDS = 5
_MAX_CONNECTION_SECONDS = 30
_FINAL_DISCONNECT_SECONDS = 5


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
        self._connect_not_before = 0.0
        self._request_pending = False
        self._connect_task: asyncio.Task[None] | None = None
        self._stopped = False
        self._disconnecting = False

    def request_connection(self) -> bool:
        """Schedule one rate-limited connection attempt."""
        if not self._reserve_connection():
            return False
        self._connect_task = self._hass.async_create_task(
            self.async_ensure_connected(_reserved=True)
        )
        return True

    def _reserve_connection(self) -> bool:
        if self._stopped or self._disconnecting:
            return False
        if self._client is not None and self._client.is_connected:
            return False
        loop = asyncio.get_running_loop()
        if (
            self._lock.locked()
            or self._request_pending
            or loop.time() < self._connect_not_before
        ):
            return False
        self._request_pending = True
        self._connect_not_before = loop.time() + _CONNECT_DEBOUNCE_SECONDS
        return True

    async def async_ensure_connected(self, *, _reserved: bool = False) -> None:
        if not _reserved and not self._reserve_connection():
            return
        self._connect_task = asyncio.current_task()
        try:
            async with self._lock:
                if self._stopped:
                    return
                if self._client is not None and self._client.is_connected:
                    return
                try:
                    async with asyncio.timeout(_CONNECT_TIMEOUT_SECONDS):
                        await self._async_connect()
                except Exception as err:
                    if self._on_failure is not None:
                        self._on_failure()
                    _LOGGER.debug(
                        "GATT connection failed for %s: %s",
                        self._model.model_name,
                        type(err).__name__,
                    )
        finally:
            self._request_pending = False
            self._connect_task = None

    async def _async_connect(self) -> None:
        from bleak_retry_connector import (
            BleakClientWithServiceCache,
            establish_connection,
        )
        from homeassistant.components import bluetooth as ha_bluetooth

        ble_device = ha_bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None or not self._matches_model_identity(ble_device):
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
        self._client = client
        try:
            notify = self._resolve_notify(client.services)
            if notify is None:
                raise RuntimeError("required notify characteristic not found")
            self._schedule_disconnect(_MAX_CONNECTION_SECONDS)

            def notification(sender: Any, data: bytearray) -> None:
                if self._client is client and not self._stopped:
                    self._notification(sender, data)

            await client.start_notify(notify, notification)
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
        except BaseException:
            # Cancellation (including unload/timeout) also owns client cleanup.
            await self._async_disconnect_client()
            raise

    def _matches_model_identity(self, ble_device: Any) -> bool:
        """Reject an explicit model-name conflict; nameless proxies stay usable."""
        name = getattr(ble_device, "name", None)
        return not name or name in {self._address, self._model.model_id}

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
                self._schedule_disconnect(_FINAL_DISCONNECT_SECONDS)

    def _schedule_disconnect(self, delay: int = _MAX_CONNECTION_SECONDS) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + min(delay, _MAX_CONNECTION_SECONDS)
        if (
            self._disconnect_timer is not None
            and not self._disconnect_timer.cancelled()
            and self._disconnect_timer.when() <= deadline
        ):
            return
        if self._disconnect_timer is not None:
            self._disconnect_timer.cancel()
        self._disconnect_timer = loop.call_at(
            deadline,
            lambda: self._hass.async_create_task(self._async_disconnect()),
        )

    def _disconnected(self, client: Any) -> None:
        if client is not self._client:
            return
        self._client = None
        if self._disconnect_timer is not None:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None

    async def async_stop(self) -> None:
        """Permanently stop this transport when its entry unloads or HA stops."""
        self._stopped = True
        await self._async_disconnect()

    async def _async_disconnect(self) -> None:
        self._disconnecting = True
        try:
            task = self._connect_task
            if (
                task is not None
                and task is not asyncio.current_task()
                and not task.done()
            ):
                if not task.cancelling():
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            async with self._lock:
                await self._async_disconnect_client()
        finally:
            self._request_pending = False
            self._disconnecting = False
            self._connect_not_before = (
                asyncio.get_running_loop().time() + _CONNECT_DEBOUNCE_SECONDS
            )

    async def _async_disconnect_client(self) -> None:
        if self._disconnect_timer is not None:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                async with asyncio.timeout(_DISCONNECT_TIMEOUT_SECONDS):
                    await client.disconnect()
            except Exception as err:
                _LOGGER.debug("GATT disconnect failed: %s", type(err).__name__)
