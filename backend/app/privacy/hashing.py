"""Hashing helpers for integrity and deterministic development output."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_probability(value: str) -> float:
    """Return a reproducible [0, 1] value without using patient data."""

    raw = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)

