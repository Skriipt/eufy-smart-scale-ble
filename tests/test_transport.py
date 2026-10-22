"""Short-lived GATT transport regression tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.eufy_smart_scale_ble.gatt import EufyGattSession
from custom_components.eufy_smart_scale_ble.model_registry import SUPPORTED_MODELS
from custom_components.eufy_smart_scale_ble.protocol_capture import ProtocolCapture
from custom_components.eufy_smart_scale_ble.protocols.legacy_t9140 import (
    NOTIFY_CANDIDATES,
)


class FakeServices:
    def __init__(self, available: set[str]) -> None:
        self.available = available

    def get_characteristic(self, uuid: str):
        return uuid if uuid in self.available else None


def session(model_id: str) -> EufyGattSession:
    return EufyGattSession(
        SimpleNamespace(async_create_task=lambda coro: asyncio.create_task(coro)),
        "synthetic-address",
        SUPPORTED_MODELS[model_id],
        lambda _event: None,
        capture=ProtocolCapture(),
    )


def test_resolves_onebyone_notify_characteristic() -> None:
    characteristic = "0000fff4-0000-1000-8000-00805f9b34fb"
    assert (
        session("eufy T9120")._resolve_notify(FakeServices({characteristic}))
        == characteristic
    )


def test_resolves_first_available_t9140_notify_characteristic() -> None:
    available = {NOTIFY_CANDIDATES[1]}
    assert (
        session("eufy T9140")._resolve_notify(FakeServices(available))
        == NOTIFY_CANDIDATES[1]
    )


def test_rejects_gatt_device_with_conflicting_model_name() -> None:
    transport = session("eufy T9120")
    assert not transport._matches_model_identity(SimpleNamespace(name="eufy T9140"))
    assert transport._matches_model_identity(SimpleNamespace(name=None))
    assert transport._matches_model_identity(SimpleNamespace(name="synthetic-address"))


async def test_concurrent_connect_requests_collapse_to_one_attempt() -> None:
    transport = session("eufy T9120")
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def connect() -> None:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()

    transport._async_connect = connect  # type: ignore[method-assign]
    first = asyncio.create_task(transport.async_ensure_connected())
    await started.wait()
    await transport.async_ensure_connected()
    release.set()
    await first
    assert calls == 1


async def test_immediate_failed_connect_requests_are_debounced() -> None:
    transport = session("eufy T9120")
    calls = 0

    async def connect() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic failure")

    transport._async_connect = connect  # type: ignore[method-assign]
    await transport.async_ensure_connected()
    await transport.async_ensure_connected()
    assert calls == 1


async def test_repeated_advertisements_schedule_only_one_connection_task() -> None:
    transport = session("eufy T9120")
    started = asyncio.Event()
    release = asyncio.Event()

    async def connect() -> None:
        started.set()
        await release.wait()

    transport._async_connect = connect  # type: ignore[method-assign]
    assert transport.request_connection()
    assert not transport.request_connection()
    await started.wait()
    release.set()
    await asyncio.sleep(0)


async def test_connected_request_does_not_extend_disconnect_deadline() -> None:
    transport = session("eufy T9120")
    transport._client = SimpleNamespace(is_connected=True)
    transport._schedule_disconnect(delay=30)
    deadline = transport._disconnect_timer
    await transport.async_ensure_connected()
    assert transport._disconnect_timer is deadline
    transport._client = None
    await transport.async_stop()


async def test_short_disconnect_deadline_cannot_be_extended() -> None:
    transport = session("eufy T9120")
    transport._schedule_disconnect(delay=5)
    deadline = transport._disconnect_timer
    transport._schedule_disconnect(delay=30)
    assert transport._disconnect_timer is deadline
    await transport.async_stop()


async def test_disconnect_delay_is_capped_at_thirty_seconds() -> None:
    transport = session("eufy T9120")
    loop = asyncio.get_running_loop()
    transport._schedule_disconnect(delay=300)
    assert transport._disconnect_timer is not None
    remaining = transport._disconnect_timer.when() - loop.time()
    assert 29 < remaining <= 30
    await transport.async_stop()


async def test_stop_disconnects_connected_client() -> None:
    disconnected = False

    class Client:
        is_connected = True

        async def disconnect(self) -> None:
            nonlocal disconnected
            disconnected = True

    transport = session("eufy T9120")
    transport._client = Client()
    await transport.async_stop()
    assert disconnected
    assert transport._client is None


@pytest.fixture
def connected_client(monkeypatch):
    from bleak_retry_connector import establish_connection
    from homeassistant.components import bluetooth

    client = SimpleNamespace(
        is_connected=True,
        services=FakeServices({"0000fff4-0000-1000-8000-00805f9b34fb"}),
        start_notify=AsyncMock(),
        disconnect=AsyncMock(),
    )
    monkeypatch.setattr(
        bluetooth,
        "async_ble_device_from_address",
        lambda *args, **kwargs: SimpleNamespace(name=None),
    )
    monkeypatch.setattr(
        f"{establish_connection.__module__}.establish_connection",
        AsyncMock(return_value=client),
    )
    return client


async def test_stop_cancels_pending_connection(connected_client, monkeypatch) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def establish(*args, **kwargs):
        started.set()
        await release.wait()
        return connected_client

    monkeypatch.setattr("bleak_retry_connector.establish_connection", establish)
    transport = session("eufy T9120")
    assert transport.request_connection()
    await started.wait()
    await transport.async_stop()
    release.set()
    await asyncio.sleep(0)
    try:
        assert transport._client is None
        assert not transport.request_connection()
        connected_client.start_notify.assert_not_awaited()
    finally:
        await transport.async_stop()


async def test_failed_notify_disconnects_immediately(connected_client) -> None:
    connected_client.start_notify.side_effect = RuntimeError("synthetic failure")
    transport = session("eufy T9120")
    await transport.async_ensure_connected()
    try:
        connected_client.disconnect.assert_awaited_once()
        assert transport._client is None
        assert transport._disconnect_timer is None
    finally:
        await transport.async_stop()


async def test_old_disconnect_callback_cannot_clear_new_connection() -> None:
    transport = session("eufy T9120")
    current = SimpleNamespace(is_connected=True, disconnect=AsyncMock())
    transport._client = current
    transport._schedule_disconnect()
    deadline = transport._disconnect_timer
    transport._disconnected(SimpleNamespace(is_connected=False))
    try:
        assert transport._client is current
        assert transport._disconnect_timer is deadline
    finally:
        await transport.async_stop()


async def test_connection_setup_is_bounded(monkeypatch) -> None:
    transport = session("eufy T9120")
    monkeypatch.setattr(
        "custom_components.eufy_smart_scale_ble.gatt._CONNECT_TIMEOUT_SECONDS",
        0.01,
        raising=False,
    )

    async def stalled_connect():
        await asyncio.Event().wait()

    transport._async_connect = stalled_connect
    await asyncio.wait_for(transport.async_ensure_connected(), timeout=0.2)
    assert not transport._request_pending


async def test_connection_error_does_not_log_private_details(caplog) -> None:
    transport = session("eufy T9120")

    async def failed_connect():
        raise RuntimeError("synthetic-private-address-and-payload")

    transport._async_connect = failed_connect
    await transport.async_ensure_connected()
    assert "GATT connection failed" in caplog.text
    assert "synthetic-private-address-and-payload" not in caplog.text


@pytest.mark.parametrize("model", ["eufy T9120", "eufy T9140"])
async def test_notify_battery_and_late_callback_lifecycle(
    connected_client, model
) -> None:
    from custom_components.eufy_smart_scale_ble.device import EufyScaleDevice
    from tests.fixtures.builders import (
        build_onebyone_frame,
        build_t9140_impedance,
        build_t9140_weight,
    )

    device = EufyScaleDevice()
    transport = session(model)
    transport._on_event = device.process_event
    transport._allow_experimental_impedance = True
    transport._capture.enabled = True
    connected_client.services.available.update(
        {
            NOTIFY_CANDIDATES[0],
            "00002a19-0000-1000-8000-00805f9b34fb",
        }
    )
    final = (
        build_onebyone_frame(weight_hundredths=6000, impedance_tenths=5000, final=True)
        if model == "eufy T9120"
        else build_t9140_weight(weight_tenths=600, final=True)
    )

    async def start_notify(characteristic, callback):
        callback(characteristic, bytearray(final))

    connected_client.start_notify.side_effect = start_notify
    connected_client.read_gatt_char = AsyncMock(return_value=b"\x50")
    await transport.async_ensure_connected()
    notify = connected_client.start_notify.call_args.args[1]
    if model == "eufy T9140":
        notify(None, bytearray(build_t9140_impedance(impedance_ohm=500)))
    assert device.state.body_measurement is not None
    assert device.state.body_measurement.weight_kg == 60.0
    assert device.state.battery_percent == 80
    assert transport._disconnect_timer.when() - asyncio.get_running_loop().time() <= 5
    await transport.async_stop()
    state, frames = device.state, transport._capture.frames
    notify(None, bytearray(final))
    assert device.state == state
    assert transport._capture.frames == frames
    connected_client.disconnect.assert_awaited_once()


async def test_timed_disconnect_allows_a_later_connection(connected_client) -> None:
    transport = session("eufy T9120")
    await transport.async_ensure_connected()
    await transport._async_disconnect()
    assert (
        not transport.request_connection()
    )  # Cooldown also follows successful disconnects.
    transport._connect_not_before = 0
    await transport.async_ensure_connected()
    assert connected_client.start_notify.await_count == 2
    await transport.async_stop()


async def test_disconnect_failure_is_bounded_and_sanitized(
    connected_client, monkeypatch, caplog
) -> None:
    transport = session("eufy T9120")
    await transport.async_ensure_connected()
    monkeypatch.setattr(
        "custom_components.eufy_smart_scale_ble.gatt._DISCONNECT_TIMEOUT_SECONDS", 0.01
    )

    async def stalled_disconnect():
        await asyncio.Event().wait()

    connected_client.disconnect.side_effect = stalled_disconnect
    await asyncio.wait_for(transport.async_stop(), timeout=0.2)
    assert transport._client is None
    assert "GATT disconnect failed: TimeoutError" in caplog.text


async def test_concurrent_timeout_and_unload_do_not_cancel_client_cleanup(
    connected_client,
) -> None:
    notifying = asyncio.Event()
    disconnecting = asyncio.Event()
    release = asyncio.Event()
    disconnected = False

    async def start_notify(*args):
        notifying.set()
        await asyncio.Event().wait()

    async def disconnect():
        nonlocal disconnected
        disconnecting.set()
        await release.wait()
        disconnected = True

    connected_client.start_notify.side_effect = start_notify
    connected_client.disconnect.side_effect = disconnect
    transport = session("eufy T9120")
    transport.request_connection()
    await notifying.wait()
    timeout = asyncio.create_task(transport._async_disconnect())
    await disconnecting.wait()
    unload = asyncio.create_task(transport.async_stop())
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(timeout, unload)
    assert disconnected
