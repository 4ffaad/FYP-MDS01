"""Hashing helpers for integrity and deterministic development output."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Calculate a SHA-256 integrity digest for a file.

    Parameters
    ----------
    path : str or pathlib.Path
        File whose bytes should be hashed.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest. Hashing is not encryption.
    """

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_probability(value: str) -> float:
    """Return a reproducible [0, 1] value without using patient data.

    Parameters
    ----------
    value : str
        Non-sensitive deterministic input, normally an opaque record/window
        identifier.

    Returns
    -------
    float
        Stable pseudo-probability for development-only behavior.
    """

    raw = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)
