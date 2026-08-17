"""Archive and EDF validation before sensitive processing begins."""

from __future__ import annotations

from pathlib import Path

from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.privacy.deidentify import inspect_metadata


class ValidationError(ValueError):
    """Controlled validation failure safe to expose to an API client."""


def validate_edf(path: Path) -> dict:
    """Validate an EDF and return safe technical metadata.

    Parameters
    ----------
    path : pathlib.Path
        EDF file to inspect. The function reads signal data and metadata but
        does not expose patient-identifying values.

    Returns
    -------
    dict
        Duration, sampling rate, channel count, and channel labels.

    Raises
    ------
    ValidationError
        Raised when the EDF cannot be read or contains unusable signal data.
    """

    try:
        signals, sampling_rate, labels = read_uniform_edf(path)
        metadata = inspect_metadata(path)
    except Exception as exc:
        raise ValidationError("EDF file is unreadable or malformed.") from exc

    if signals.size == 0 or not labels:
        raise ValidationError("EDF file does not contain EEG signal data.")
    if sampling_rate <= 0:
        raise ValidationError("EDF sampling rate is invalid.")

    technical = metadata["technical"]
    return {
        "duration_seconds": float(technical["duration_seconds"]),
        "sampling_rate": int(sampling_rate),
        "channel_count": len(labels),
        "channel_labels": labels,
    }
