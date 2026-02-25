import base64
import hashlib
import hmac
import json
import os
from typing import Any


class SyncCryptoError(ValueError):
    pass


def derive_key(passphrase: str, salt: bytes, iterations: int = 390000) -> bytes:
    if not passphrase:
        raise SyncCryptoError('Passphrase required')
    return hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt, iterations, dklen=32)


def _keystream(key: bytes, nonce: bytes, size: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < size:
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, 'big')).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:size])


def encrypt_json(payload: dict[str, Any], key: bytes, nonce: bytes | None = None) -> tuple[bytes, bytes, str]:
    nonce = nonce or os.urandom(12)
    plain = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    stream = _keystream(key, nonce, len(plain))
    cipher = bytes(a ^ b for a, b in zip(plain, stream))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return nonce + cipher + tag, nonce, hashlib.sha256(plain).hexdigest()


def decrypt_json(ciphertext: bytes, key: bytes) -> dict[str, Any]:
    if len(ciphertext) < 44:
        raise SyncCryptoError('Ciphertext too small')
    nonce = ciphertext[:12]
    tag = ciphertext[-32:]
    cipher = ciphertext[12:-32]
    expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise SyncCryptoError('Invalid passphrase or corrupted payload')
    stream = _keystream(key, nonce, len(cipher))
    plain = bytes(a ^ b for a, b in zip(cipher, stream))
    try:
        return json.loads(plain.decode('utf-8'))
    except Exception as exc:
        raise SyncCryptoError('Failed to decode payload') from exc


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode('ascii')


def unb64(s: str) -> bytes:
    return base64.b64decode(s.encode('ascii'))
