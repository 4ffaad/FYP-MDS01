"""Build short-lived, privacy-scoped artifacts from model-positive windows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pyedflib

from backend.app.ml.interface import WindowPrediction


def detected_intervals(
    predictions: list[WindowPrediction],
    duration_seconds: float,
    context_seconds: float = 60.0,
) -> list[tuple[float, float]]:
    """Return merged recording ranges around model-positive windows.

    Parameters
    ----------
    predictions : list[WindowPrediction]
        Window-level model outputs for one recording.
    duration_seconds : float
        Full recording duration used to clamp the ranges.
    context_seconds : float
        Seconds added before and after each positive window.

    Returns
    -------
    list[tuple[float, float]]
        Non-overlapping ranges to retain, or an empty list when no window is
        model-positive.
    """

    ranges = [
        (
            max(0.0, prediction.start_seconds - context_seconds),
            min(duration_seconds, prediction.end_seconds + context_seconds),
        )
        for prediction in predictions
        if prediction.seizure_detected
    ]
    merged: list[list[float]] = []
    for start, end in sorted(ranges):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def select_window_indices(
    window_starts: np.ndarray,
    intervals: list[tuple[float, float]],
    window_seconds: float = 4.0,
) -> np.ndarray:
    """Return transformed model-window indexes overlapping retained ranges.

    Parameters
    ----------
    window_starts : numpy.ndarray
        Start time for each model window.
    intervals : list[tuple[float, float]]
        Ranges returned by :func:`detected_intervals`.
    window_seconds : float
        Duration of each model window.

    Returns
    -------
    numpy.ndarray
        Sorted integer indexes suitable for selecting model windows.
    """

    selected = [
        index
        for index, start in enumerate(window_starts.tolist())
        if any(start < end and start + window_seconds > begin for begin, end in intervals)
    ]
    return np.asarray(selected, dtype=np.int64)


def write_obfuscated_npz(
    output_path: str | Path,
    windows: np.ndarray,
    window_starts: np.ndarray,
    indexes: np.ndarray,
) -> Path:
    """Write only model-positive obfuscated windows to a temporary NPZ file.

    Parameters
    ----------
    output_path : str or pathlib.Path
        Temporary output path owned by the processing service.
    windows : numpy.ndarray
        Obfuscated model windows with shape ``(N, 1024, 18)``.
    window_starts : numpy.ndarray
        Start time for each input window.
    indexes : numpy.ndarray
        Window indexes selected for retention.

    Returns
    -------
    pathlib.Path
        Written temporary artifact path.
    """

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        model_windows=windows[indexes].astype(np.float32, copy=False),
        window_start_seconds=window_starts[indexes].astype(np.float32, copy=False),
    )
    return destination


def write_scrubbed_edf_clip(
    source_path: str | Path,
    output_path: str | Path,
    intervals: list[tuple[float, float]],
) -> Path:
    """Write selected ranges from a metadata-scrubbed EDF as a new EDF.

    The source is expected to have already been metadata-scrubbed. Signal
    samples and channel labels are preserved, while the output timeline is
    compacted and all annotation descriptions remain blank.

    Parameters
    ----------
    source_path : str or pathlib.Path
        Temporary metadata-scrubbed EDF.
    output_path : str or pathlib.Path
        Temporary clip destination.
    intervals : list[tuple[float, float]]
        Source-time ranges to retain.

    Returns
    -------
    pathlib.Path
        Written temporary EDF path.

    Raises
    ------
    ValueError
        Raised when no valid interval can be written.
    """

    if not intervals:
        raise ValueError("At least one retained interval is required.")
    source = pyedflib.EdfReader(str(source_path))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    try:
        frequencies = source.getSampleFrequencies()
        if len(set(frequencies.tolist())) != 1:
            raise ValueError("Retained EDF requires uniform channel sampling rates.")
        frequency = float(frequencies[0])
        sample_count = int(source.getNSamples()[0])
        samples_by_channel = [source.readSignal(channel, digital=True) for channel in range(source.signals_in_file)]
        slices: list[tuple[int, int, float, float]] = []
        for begin, end in intervals:
            start_index = max(0, min(sample_count, round(begin * frequency)))
            end_index = max(start_index, min(sample_count, round(end * frequency)))
            if end_index > start_index:
                slices.append((start_index, end_index, begin, end))
        if not slices:
            raise ValueError("Retained intervals do not overlap the EDF.")

        selected_samples = [
            np.concatenate([samples[start:end] for start, end, _, _ in slices])
            for samples in samples_by_channel
        ]
        signal_headers = source.getSignalHeaders()
        writer = pyedflib.EdfWriter(
            str(destination),
            source.signals_in_file,
            file_type=source.filetype,
        )
        writer.setHeader({
            "technician": "",
            "recording_additional": "",
            "patientname": "",
            "patient_additional": "",
            "patientcode": "",
            "equipment": "",
            "admincode": "",
            "sex": "",
            # Retained clips must not carry the source calendar timestamp.
            # Relative offsets are kept only for model-review alignment.
            "startdate": datetime(1970, 1, 1),
            "birthdate": "",
        })
        writer.setSignalHeaders(signal_headers)
        writer.writeSamples(selected_samples, digital=True)

        annotations, durations, _descriptions = source.readAnnotations()
        retained_offset = 0.0
        for start_index, end_index, begin, end in slices:
            source_begin = start_index / frequency
            source_end = end_index / frequency
            for onset, duration in zip(annotations, durations):
                annotation_end = float(onset + duration)
                overlap_start = max(float(onset), source_begin)
                overlap_end = min(annotation_end, source_end)
                if overlap_end > overlap_start:
                    writer.writeAnnotation(
                        retained_offset + overlap_start - source_begin,
                        overlap_end - overlap_start,
                        "",
                    )
            retained_offset += source_end - source_begin
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if writer is not None:
            writer.close()
        source.close()
    return destination
