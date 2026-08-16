"""Shared, read-only EDF loading helpers."""

from pathlib import Path

import numpy as np
import pyedflib


def read_uniform_edf(edf_path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read an EDF whose channels use one sampling frequency.

    The preprocessing pipeline operates on a rectangular
    ``(channels, samples)`` array, so mixed-rate EDFs are rejected instead of
    silently resampling or truncating channels.
    """
    reader = pyedflib.EdfReader(str(edf_path))
    try:
        frequencies = reader.getSampleFrequencies()
        if len(set(frequencies.tolist())) != 1:
            raise ValueError("Channels have different sampling rates.")

        sample_counts = reader.getNSamples()
        if len(set(sample_counts.tolist())) != 1:
            raise ValueError("Channels have different sample counts.")

        sampling_rate = int(frequencies[0])
        signals = np.asarray(
            [reader.readSignal(channel) for channel in range(reader.signals_in_file)]
        )
        return signals, sampling_rate, reader.getSignalLabels()
    finally:
        reader.close()
