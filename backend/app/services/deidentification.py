"""Legacy import compatibility for the relocated privacy service."""

from backend.app.privacy.deidentify import (
    deidentify_edf,
    generate_record_id,
    inspect_metadata,
)

__all__ = [
    "deidentify_edf",
    "generate_record_id",
    "inspect_metadata",
]
