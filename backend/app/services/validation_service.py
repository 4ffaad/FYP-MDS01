"""Archive and EEG validation before sensitive processing begins."""

from __future__ import annotations

from pathlib import Path

import pyedflib

from backend.app.eeg.io import validate_legacy_nicolet_e, validate_nicolet


class ValidationError(ValueError):
    """Controlled validation failure safe to expose to an API client."""


def validate_eeg(path: Path) -> dict:
    """Validate an EDF or Nicolet recording and return safe metadata."""

    if path.suffix.lower() == ".edf":
        metadata = validate_edf(path)
        metadata["format"] = "edf"
        return metadata
    if path.suffix.lower() == ".data":
        try:
            metadata = validate_nicolet(path)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return {
            "format": metadata.format,
            "duration_seconds": metadata.duration_seconds,
            "sampling_rate": metadata.sampling_rate,
            "channel_count": metadata.channel_count,
            "channel_labels": metadata.channel_labels,
        }
    if path.suffix.lower() == ".e":
        try:
            metadata = validate_legacy_nicolet_e(path)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return {
            "format": metadata.format,
            "duration_seconds": metadata.duration_seconds,
            "sampling_rate": metadata.sampling_rate,
            "channel_count": metadata.channel_count,
            "channel_labels": metadata.channel_labels,
            "conversion_details": metadata.conversion_details,
        }
    raise ValidationError("Unsupported EEG format. Use EDF/EDF+, Nicolet .data with .head, or legacy Nicolet .e.")


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
