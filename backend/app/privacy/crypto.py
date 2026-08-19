"""Small AES-GCM helpers for transient private EEG storage."""

from __future__ import annotations

import base64
import binascii
import os


class CryptoError(ValueError):
    """Raised when a required encryption secret is unavailable or invalid."""


def read_base64_key(environment_name: str) -> bytes:
    """Return a required 32-byte base64 key from the process environment."""

    value = os.getenv(environment_name)
    if not value:
        raise CryptoError(f"{environment_name} must be configured.")
    try:
        key = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CryptoError(f"{environment_name} must be valid base64.") from exc
    if len(key) != 32:
        raise CryptoError(f"{environment_name} must decode to exactly 32 bytes.")
    return key
