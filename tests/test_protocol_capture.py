from custom_components.eufy_smart_scale_ble.protocol_capture import ProtocolCapture


def test_capture_is_off_and_empty_by_default() -> None:
    capture = ProtocolCapture()
    capture.add(b"synthetic")
    assert capture.frames == ()


def test_capture_is_memory_only_and_bounded() -> None:
    capture = ProtocolCapture(enabled=True, max_frames=2)
    capture.add(b"one")
    capture.add(b"two")
    capture.add(b"three")
    assert capture.frames == (b"two", b"three")
    capture.clear()
    assert capture.frames == ()
