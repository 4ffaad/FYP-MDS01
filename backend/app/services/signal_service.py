"""Bounded, local-development signal previews from retained positive clips."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyedflib
from sqlmodel import Session

from backend.app.core.config import ENABLE_FULL_SIGNAL_PREVIEW, ENABLE_SIGNAL_PREVIEW
from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.repository import list_predictions
from backend.app.eeg.model_input import MODEL_CHANNELS, MODEL_SAMPLING_RATE
from backend.app.privacy.retention import detected_intervals
from backend.app.services.storage_service import SessionStorage


class SignalPreviewUnavailable(ValueError):
    """Raised when a safe retained signal cannot be shown."""


def build_signal_preview(
    db: Session,
    session: EEGSession,
    record: EEGRecording,
    storage: SessionStorage,
    start_seconds: float,
    duration_seconds: float,
    max_points: int,
) -> dict:
    """Read a bounded retained positive clip and attach model alert intervals.

    Only metadata-scrubbed EDF clips or obfuscated NPZ windows are materialized
    temporarily. The plaintext file is removed in a ``finally`` block.
    """

    if not ENABLE_SIGNAL_PREVIEW:
        raise SignalPreviewUnavailable("Waveform access is disabled for this privacy-first prototype.")
    if record.status.value != "inferred" or not record.retained_artifact_path:
        raise SignalPreviewUnavailable("No retained model-positive signal is available for this recording.")

    predictions = list_predictions(db, record.id or 0)
    flagged = [item for item in predictions if item.seizure_detected]
    if not flagged:
        raise SignalPreviewUnavailable("No model-positive signal is available for this recording.")

    artifact = Path(record.retained_artifact_path)
    if not artifact.exists():
        raise SignalPreviewUnavailable("The retained signal preview is no longer available.")

    suffix = ".edf" if artifact.name.endswith(".edf.enc") else ".npz" if artifact.name.endswith(".npz.enc") else ""
    if not suffix:
        raise SignalPreviewUnavailable("The retained signal format is unavailable.")
    temporary_name = f"{record.record_id}.preview{suffix}"
    temporary_path = storage.materialize_retained_artifact(session.session_id, artifact, temporary_name)
    try:
        if suffix == ".edf":
            payload = _read_edf_preview(
                temporary_path,
                flagged,
                record.duration_seconds or 0.0,
                start_seconds,
                duration_seconds,
                max_points,
                full_preview=ENABLE_FULL_SIGNAL_PREVIEW,
            )
            representation = "metadata-scrubbed"
        else:
            payload = _read_npz_preview(
                temporary_path,
                flagged,
                start_seconds,
                duration_seconds,
                max_points,
            )
            representation = "signal-obfuscated"
        payload.update({
            "record_id": record.record_id,
            "representation": representation,
            "sampling_rate": MODEL_SAMPLING_RATE,
            "flagged_intervals": [
                {
                    "start_seconds": max(start_seconds, float(item.start_seconds)),
                    "end_seconds": min(start_seconds + duration_seconds, float(item.end_seconds)),
                }
                for item in flagged
                if item.end_seconds > start_seconds and item.start_seconds < start_seconds + duration_seconds
            ],
        })
        return payload
    finally:
        temporary_path.unlink(missing_ok=True)


def _read_edf_preview(
    path: Path,
    flagged: list,
    recording_duration: float,
    start_seconds: float,
    duration_seconds: float,
    max_points: int,
    *,
    full_preview: bool,
) -> dict:
    """Read model channels from a compacted scrubbed EDF with source times."""

    intervals = [(0.0, recording_duration)] if full_preview else detected_intervals(flagged, recording_duration)
    requested_end = start_seconds + duration_seconds
    reader = pyedflib.EdfReader(str(path))
    try:
        labels = [label.strip() for label in reader.getSignalLabels()]
        index_by_label = {label: index for index, label in enumerate(labels)}
        missing = [label for label in MODEL_CHANNELS if label not in index_by_label]
        if missing:
            raise SignalPreviewUnavailable("The retained signal is missing model channels.")
        frequencies = reader.getSampleFrequencies()
        frequency = float(frequencies[0])
        source_samples: list[list[np.ndarray]] = [[] for _ in MODEL_CHANNELS]
        timestamps: list[np.ndarray] = []
        segments: list[dict] = []
        compact_offset = 0.0
        for source_start, source_end in intervals:
            overlap_start = max(source_start, start_seconds)
            overlap_end = min(source_end, requested_end)
            if overlap_end > overlap_start:
                begin = int(round((compact_offset + overlap_start - source_start) * frequency))
                end = int(round((compact_offset + overlap_end - source_start) * frequency))
                for channel_index, channel in enumerate(MODEL_CHANNELS):
                    source_samples[channel_index].append(
                        reader.readSignal(index_by_label[channel], start=begin, n=end - begin)
                    )
                count = max(0, end - begin)
                timestamps.append(overlap_start + np.arange(count, dtype=np.float64) / frequency)
                segments.append({"source_start_seconds": overlap_start, "source_end_seconds": overlap_end})
            compact_offset += source_end - source_start
        if not timestamps:
            raise SignalPreviewUnavailable("No retained signal overlaps the requested interval.")
        time_values = np.concatenate(timestamps)
        channels = np.vstack([np.concatenate(chunks) for chunks in source_samples])
        channels, time_values = _downsample(channels, time_values, max_points)
        return {
            "channels": [
                {"label": label, "samples": [round(float(value), 6) for value in channels[index]]}
                for index, label in enumerate(MODEL_CHANNELS)
            ],
            "time_seconds": [round(float(value), 6) for value in time_values],
            "segments": segments,
        }
    finally:
        reader.close()


def _read_npz_preview(
    path: Path,
    flagged: list,
    start_seconds: float,
    duration_seconds: float,
    max_points: int,
) -> dict:
    """Read obfuscated model windows while retaining their source timestamps."""

    end_seconds = start_seconds + duration_seconds
    with np.load(path) as payload:
        windows = payload["model_windows"].astype(np.float32, copy=False)
        starts = payload["window_start_seconds"].astype(np.float64, copy=False)
        labels = [str(value) for value in payload.get("channel_labels", MODEL_CHANNELS)]
    selected_windows: list[np.ndarray] = []
    timestamps: list[np.ndarray] = []
    segments: list[dict] = []
    requested_start = int(round(start_seconds * MODEL_SAMPLING_RATE))
    emitted_until = requested_start
    requested_end = int(round(end_seconds * MODEL_SAMPLING_RATE))
    for index in np.argsort(starts, kind="stable"):
        window = windows[index]
        window_start = float(starts[index])
        window_start_sample = int(round(window_start * MODEL_SAMPLING_RATE))
        window_end_sample = window_start_sample + window.shape[0]
        begin_sample = max(emitted_until, requested_start, window_start_sample)
        finish_sample = min(requested_end, window_end_sample)
        if finish_sample <= begin_sample:
            continue
        begin = begin_sample - window_start_sample
        finish = finish_sample - window_start_sample
        selected_windows.append(window[begin:finish])
        timestamps.append(np.arange(begin_sample, finish_sample, dtype=np.float64) / MODEL_SAMPLING_RATE)
        segment_start = begin_sample / MODEL_SAMPLING_RATE
        segment_end = finish_sample / MODEL_SAMPLING_RATE
        if segments and segment_start <= segments[-1]["source_end_seconds"]:
            segments[-1]["source_end_seconds"] = max(segments[-1]["source_end_seconds"], segment_end)
        else:
            segments.append({
                "source_start_seconds": segment_start,
                "source_end_seconds": segment_end,
            })
        emitted_until = finish_sample
    if not selected_windows:
        raise SignalPreviewUnavailable("No retained signal overlaps the requested interval.")
    samples = np.concatenate(selected_windows, axis=0).T
    time_values = np.concatenate(timestamps)
    samples, time_values = _downsample(samples, time_values, max_points)
    return {
        "channels": [
            {"label": labels[index] if index < len(labels) else MODEL_CHANNELS[index], "samples": [round(float(value), 6) for value in samples[index]]}
            for index in range(min(samples.shape[0], len(MODEL_CHANNELS)))
        ],
        "time_seconds": [round(float(value), 6) for value in time_values],
        "segments": segments,
    }


def _downsample(samples: np.ndarray, times: np.ndarray, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Downsample all channels using one shared index array."""

    if len(times) <= max_points:
        return samples, times
    indexes = np.linspace(0, len(times) - 1, max_points, dtype=np.int64)
    return samples[:, indexes], times[indexes]
