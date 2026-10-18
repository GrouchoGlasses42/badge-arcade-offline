"""Optional desktop import of an archived EUR BOSS payload; keys stay local."""
from __future__ import annotations

import hashlib
import struct

from badge_catalog import read_sarc

EUR_TITLE_ID = 0x0004000000153600


def open_spotpass(data: bytes, boot9: bytes | None = None) -> bytes:
    """Return a SARC payload, validating BOSS framing and both SHA-256 hashes.

    This checks integrity and the target title, not Nintendo's RSA signature.
    Plain, already decrypted SARCs are also accepted.
    """
    if data.startswith(b"SARC"):
        read_sarc(data)
        return data
    if len(data) < 0x296 or data[:4] != b"boss":
        raise ValueError("Expected a decrypted SARC or an encrypted 3DS BOSS container")
    version, size = struct.unpack_from(">II", data, 4)
    if version != 0x10001 or size != len(data):
        raise ValueError("Invalid BOSS version or container length")
    if boot9 is None:
        raise ValueError("Encrypted SpotPass packs require --boot9 (your local boot9 dump)")
    if len(boot9) not in (0x8000, 0x10000):
        raise ValueError("Expected a 32 KiB protected or 64 KiB full boot9 dump")
    offset = len(boot9) - 0x8000 + 0x5BD0
    key = boot9[offset:offset + 16]
    try:
        from Crypto.Cipher import AES
    except ImportError as exc:
        raise ValueError("Encrypted packs need pycryptodome: install requirements-spotpass.txt") from exc
    body = AES.new(key, AES.MODE_CTR, nonce=data[0x1C:0x28], initial_value=1).decrypt(data[0x28:])
    if hashlib.sha256(body[:0x12] + bytes(2)).digest() != body[0x12:0x32]:
        raise ValueError("BOSS content hash mismatch: wrong boot9 dump or damaged pack")
    if struct.unpack_from(">H", body, 0x10)[0] != 1:
        raise ValueError("Expected one BOSS payload")
    program, _, _, length = struct.unpack_from(">QIII", body, 0x132)
    if program != EUR_TITLE_ID:
        raise ValueError("SpotPass pack is not for EUR Badge Arcade")
    payload = body[0x26E:]
    if length != len(payload):
        raise ValueError("BOSS payload length mismatch")
    if hashlib.sha256(body[0x132:0x14E] + bytes(2) + payload).digest() != body[0x14E:0x16E]:
        raise ValueError("BOSS payload hash mismatch")
    read_sarc(payload)
    return payload

