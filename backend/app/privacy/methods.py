"""Canonical privacy-profile parsing for upload and processing requests."""

from __future__ import annotations

import json
from collections.abc import Iterable


METADATA_SCRUB = "metadata-scrub"
SIGNAL_OBFUSCATION = "signal-obfuscation"
CANONICAL_BASELINE = METADATA_SCRUB
CANONICAL_COMBINED = f"{METADATA_SCRUB}+{SIGNAL_OBFUSCATION}"
SUPPORTED_PRIVACY_METHODS = (METADATA_SCRUB, SIGNAL_OBFUSCATION)


def normalize_privacy_methods(
    methods: Iterable[str] | str | None = None,
    legacy_method: str | None = None,
    allow_historical_aliases: bool = False,
) -> tuple[str, ...]:
    """Return the safe, ordered privacy operations for one upload.

    Parameters
    ----------
    methods : iterable[str] or str or None
        New ordered method list, or a JSON-encoded list from a form field.
    legacy_method : str or None
        Existing single-method field retained for compatibility.
    allow_historical_aliases : bool
        Allow old database-only labels while decoding persisted rows.

    Returns
    -------
    tuple[str, ...]
        Metadata scrubbing followed by optional signal obfuscation.

    Raises
    ------
    ValueError
        Raised when the request is malformed or names an unsupported method.
    """

    raw_methods: list[str]
    if methods is None:
        raw_methods = [legacy_method or METADATA_SCRUB]
    elif isinstance(methods, str):
        value = methods.strip()
        if not value:
            raw_methods = [legacy_method or METADATA_SCRUB]
        elif value.startswith("["):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("privacy_methods must be a JSON array.") from exc
            if not isinstance(decoded, list):
                raise ValueError("privacy_methods must be a JSON array.")
            raw_methods = [str(item) for item in decoded]
        else:
            raw_methods = [item for item in value.split(",") if item.strip()]
    else:
        raw_methods = [str(item) for item in methods]

    aliases = {"none": METADATA_SCRUB}
    if allow_historical_aliases:
        aliases.update({
            "control": METADATA_SCRUB,
            "raw-control": METADATA_SCRUB,
            "cancellable-psd-template": SIGNAL_OBFUSCATION,
            "cancellable-signal-projection": SIGNAL_OBFUSCATION,
        })
    cleaned: list[str] = []
    for item in raw_methods:
        value = aliases.get(item.strip().lower(), item.strip().lower())
        if not value:
            continue
        if value == CANONICAL_COMBINED:
            value = SIGNAL_OBFUSCATION
        if value not in SUPPORTED_PRIVACY_METHODS:
            raise ValueError("privacy method is not supported.")
        if value not in cleaned:
            cleaned.append(value)

    if METADATA_SCRUB not in cleaned:
        cleaned.insert(0, METADATA_SCRUB)
    if SIGNAL_OBFUSCATION in cleaned:
        return (METADATA_SCRUB, SIGNAL_OBFUSCATION)
    return (METADATA_SCRUB,)


def canonical_privacy_profile(methods: Iterable[str] | str | None = None) -> str:
    """Return the compact database value for an ordered privacy profile.

    Parameters
    ----------
    methods : iterable[str] or str or None
        Privacy operations to normalize.

    Returns
    -------
    str
        ``metadata-scrub`` or ``metadata-scrub+signal-obfuscation``.
    """

    normalized = normalize_privacy_methods(methods)
    return CANONICAL_COMBINED if SIGNAL_OBFUSCATION in normalized else CANONICAL_BASELINE


def methods_from_profile(profile: str | None) -> tuple[str, ...]:
    """Decode a stored profile, including historical single-method values.

    Parameters
    ----------
    profile : str or None
        Stored privacy profile value.

    Returns
    -------
    tuple[str, ...]
        Ordered privacy operations used by the pipeline and public adapters.
    """

    return normalize_privacy_methods(profile or METADATA_SCRUB, allow_historical_aliases=True)
