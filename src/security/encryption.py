import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV = "FIELD_ENCRYPTION_KEY"


def _get_key() -> bytes:
    key = os.getenv(KEY_ENV, "").encode()
    if not key:
        # derive from placeholder for dev only; replace in prod
        key = hashlib.sha256(b"dev-placeholder").digest()
    # normalize to 32 bytes
    if len(key) in (32,):
        return key
    try:
        return base64.b64decode(key)
    except Exception:
        return hashlib.sha256(key).digest()


def encrypt(plaintext: bytes, aad: bytes = b"") -> bytes:
    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ct


def decrypt(blob: bytes, aad: bytes = b"") -> bytes:
    aesgcm = AESGCM(_get_key())
    nonce, ct = blob[:12], blob[12:]
    return aesgcm.decrypt(nonce, ct, aad)
