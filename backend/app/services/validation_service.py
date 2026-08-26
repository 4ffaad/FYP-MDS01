"""Archive and EDF validation before sensitive processing begins."""

from __future__ import annotations

from pathlib import Path

import pyedflib


class ValidationError(ValueError):
    """Controlled validation failure safe to expose to an API client."""


def validate_edf(path: Path) -> dict:
    """Validate an EDF and return safe technical metadata.

    Parameters
    ----------
    path : pathlib.Path
        EDF file to inspect. Only technical headers and sample counts are read;
        patient-identifying values are neither returned nor logged.

    Returns
    -------
    dict
        Duration, sampling rate, channel count, and channel labels.

    Raises
    ------
    ValidationError
        Raised when the EDF cannot be read or contains unusable signal data.
    """

    reader = None
    try:
        reader = pyedflib.EdfReader(str(path))
        labels = reader.getSignalLabels()
        frequencies = reader.getSampleFrequencies()
        sample_counts = reader.getNSamples()
        if not labels or not len(frequencies) or not len(sample_counts):
            raise ValidationError("EDF file does not contain EEG signal data.")
        if len(set(frequencies.tolist())) != 1 or len(set(sample_counts.tolist())) != 1:
            raise ValidationError("EDF channels must use one sampling rate and sample count.")
        sampling_rate = int(frequencies[0])
        if sampling_rate <= 0 or int(sample_counts[0]) <= 0:
            raise ValidationError("EDF sampling information is invalid.")
        return {
            "duration_seconds": float(reader.getFileDuration()),
            "sampling_rate": sampling_rate,
            "channel_count": len(labels),
            "channel_labels": labels,
        }
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("EDF file is unreadable or malformed.") from exc
    finally:
        if reader is not None:
            reader.close()
