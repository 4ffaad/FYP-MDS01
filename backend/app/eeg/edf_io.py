"""Shared, read-only EDF loading helpers."""

from pathlib import Path

import numpy as np
import pyedflib

from backend.app.eeg.contracts import EEGInputContractError, require_model_sampling_rate


def reject_discontinuous_edf(edf_path: str | Path) -> None:
    """Reject EDF+D/BDF+D before a reader can flatten acquisition gaps."""

    with Path(edf_path).open("rb") as source:
        fixed_header = source.read(256)
    if len(fixed_header) == 256 and fixed_header[192:197].upper() in {b"EDF+D", b"BDF+D"}:
        raise EEGInputContractError(
            "Discontinuous EDF+ recordings are not supported; segment-aware windowing is required."
        )


def validated_edf_sampling_rate(frequencies: object) -> int:
    """Validate uniform EDF channel rates against the model's exact input rate."""

    rates = np.asarray(frequencies, dtype=np.float64)
    if rates.ndim != 1 or rates.size == 0 or not np.isfinite(rates).all() or np.any(rates <= 0):
        raise EEGInputContractError("EDF sampling information is invalid.")
    if np.any(rates != rates[0]):
        raise EEGInputContractError("EDF channels must use one sampling rate.")
    return require_model_sampling_rate(float(rates[0]), "EDF")


def read_uniform_edf(edf_path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read an EDF whose channels use one sampling frequency.

    The preprocessing pipeline operates on a rectangular
    ``(channels, samples)`` array, so mixed-rate EDFs are rejected instead of
    silently resampling or truncating channels.
    """
    reject_discontinuous_edf(edf_path)
    reader = pyedflib.EdfReader(str(edf_path))
    try:
        frequencies = reader.getSampleFrequencies()
        sampling_rate = validated_edf_sampling_rate(frequencies)

        sample_counts = reader.getNSamples()
        if len(set(sample_counts.tolist())) != 1:
            raise ValueError("Channels have different sample counts.")

        signals = np.asarray(
            [reader.readSignal(channel) for channel in range(reader.signals_in_file)]
        )
        return signals, sampling_rate, reader.getSignalLabels()
    finally:
        reader.close()
