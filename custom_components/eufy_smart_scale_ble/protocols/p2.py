"""Eufy P2/P2 Pro advertisement and authenticated GATT protocol helpers."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .base import MeasurementEvent, MeasurementPhase, valid_heart_rate, valid_weight

IV = b"0000000000000000"


def parse_p2_advertisement(
    raw: object, *, supports_heart_rate: bool
) -> MeasurementEvent | None:
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return None
    data = bytes(raw)
    if len(data) != 19 or data[6] != 0xCF:
        return None
    weight = int.from_bytes(data[9:11], "little") / 100
    if not valid_weight(weight):
        return None
    final = data[15] == 0
    heart_rate = None
    if supports_heart_rate and data[8] >> 6 == 0b11:
        candidate = data[7]
        if valid_heart_rate(candidate):
            heart_rate = candidate
    return MeasurementEvent(
        phase=MeasurementPhase.LOCKED if final else MeasurementPhase.LIVE,
        weight_kg=weight,
        heart_rate_bpm=heart_rate,
        status="locked" if final else "live",
    )


def parse_p2_gatt_weight(data: bytes) -> MeasurementEvent | None:
    if len(data) != 16 or data[0] != 0xCF or data[2] != 0:
        return None
    weight = int.from_bytes(data[6:8], "little") / 100
    if not valid_weight(weight):
        return None
    final = data[12] == 0
    return MeasurementEvent(
        phase=MeasurementPhase.LOCKED if final else MeasurementPhase.LIVE,
        weight_kg=weight,
        status="locked" if final else "live",
    )


def xor_checksum(data: bytes) -> int:
    result = 0
    for value in data:
        result ^= value
    return result


def key_from_mac(address: str) -> bytes:
    normalized = address.replace(":", "").replace("-", "").upper()
    if len(normalized) != 12:
        raise ValueError("Bluetooth address must contain 12 hexadecimal digits")
    bytes.fromhex(normalized)
    return hashlib.md5(normalized.encode(), usedforsecurity=False).digest()


def _encrypt(value: str, key: bytes) -> str:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(value.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).hex()


def _decrypt(value: bytes, key: bytes) -> str:
    decryptor = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    decrypted = decryptor.update(value) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(decrypted) + unpadder.finalize()).decode()


def segment(hex_payload: str, prefix: int) -> tuple[bytes, ...]:
    total_bytes = len(hex_payload) // 2
    chunks = [hex_payload[i : i + 30] for i in range(0, len(hex_payload), 30)]
    result: list[bytes] = []
    for index, chunk in enumerate(chunks):
        body = bytes.fromhex(
            f"{prefix:02x}{len(chunks):02x}{index:02x}{total_bytes:02x}{chunk}"
        )
        result.append(body + bytes([xor_checksum(body)]))
    return tuple(result)


@dataclass(slots=True)
class P2AuthSession:
    """Pure C0/C1/C2/C3 helper retained for future research GATT use."""

    address: str
    client_uuid: str
    key: bytes = field(init=False)
    _c1_payload: bytearray = field(default_factory=bytearray, init=False)
    _next_segment: int = field(default=0, init=False)
    device_uuid: str | None = field(default=None, init=False)
    authenticated: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if len(self.client_uuid) != 15:
            raise ValueError("client_uuid must be exactly 15 characters")
        self.key = key_from_mac(self.address)

    def c0(self) -> tuple[bytes, ...]:
        return segment(_encrypt(self.client_uuid, self.key), 0xC0)

    def handle_c1(self, data: bytes) -> bool:
        if len(data) < 6 or data[0] != 0xC1 or xor_checksum(data[:-1]) != data[-1]:
            return False
        total, index = data[1], data[2]
        if index == 0:
            self._c1_payload.clear()
            self._next_segment = 0
        if index != self._next_segment:
            return False
        self._c1_payload.extend(data[4:-1])
        self._next_segment += 1
        if index != total - 1:
            return False
        encrypted = base64.b64decode(bytes(self._c1_payload))
        self.device_uuid = _decrypt(encrypted, self.key)
        return True

    def c2(self) -> tuple[bytes, ...]:
        if self.device_uuid is None:
            raise RuntimeError("C1 must complete before C2")
        return segment(
            _encrypt(f"{self.client_uuid}_{self.device_uuid}", self.key), 0xC2
        )

    def handle_c3(self, data: bytes) -> bool:
        if len(data) < 5 or data[0] != 0xC3:
            return False
        self.authenticated = data[4] == 0
        return True
