"""Short-lived GATT transport regression tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

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
