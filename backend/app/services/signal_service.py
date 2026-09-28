"""Bounded, local-development signal previews from retained positive clips."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyedflib
from sqlmodel import Session

from backend.app.core.config import ENABLE_FULL_SIGNAL_PREVIEW, ENABLE_SIGNAL_PREVIEW
from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.repository import list_predictions
from backend.app.eeg.model_input import (
    MODEL_CHANNELS,
    MODEL_SAMPLING_RATE,
    validate_model_time_offsets,
)
from backend.app.privacy.methods import SIGNAL_OBFUSCATION, methods_from_profile
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

    Metadata-scrubbed EDF clips or transformed model-window NPZ files are
    materialized temporarily. The reported representation reflects the
    session's privacy profile, and plaintext is removed in a ``finally`` block.
    """

    if not ENABLE_SIGNAL_PREVIEW:
        raise SignalPreviewUnavailable("Waveform access is disabled for this privacy-first prototype.")
    if record.status.value != "inferred" or not record.retained_artifact_path:
        raise SignalPreviewUnavailable("No retained model-positive signal is available for this recording.")

    predictions = list_predictions(db, record.id or 0)
    flagged = [item for item in predictions if item.seizure_detected]
    if not flagged:
        raise SignalPreviewUnavailable("No model-positive signal is available for this recording.")
    try:
        validate_model_time_offsets(
            [
                start_seconds,
                start_seconds + duration_seconds,
                *(value for item in flagged for value in (item.start_seconds, item.end_seconds)),
            ]
        )
    except ValueError as exc:
        raise SignalPreviewUnavailable(str(exc)) from exc

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
            representation = (
                "signal-obfuscated"
                if SIGNAL_OBFUSCATION in methods_from_profile(session.privacy_method)
                else "metadata-scrubbed"
            )
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
            "time_seconds": [float(value) for value in time_values],
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
    """Read retained model windows while preserving their source timestamps."""

    end_seconds = start_seconds + duration_seconds
    with np.load(path) as payload:
        windows = payload["model_windows"].astype(np.float32, copy=False)
        try:
            starts = validate_model_time_offsets(payload["window_start_seconds"])
        except ValueError as exc:
            raise SignalPreviewUnavailable(str(exc)) from exc
        labels = [str(value) for value in payload.get("channel_labels", MODEL_CHANNELS)]
    selected_windows: list[np.ndarray] = []
    timestamps: list[np.ndarray] = []
    segments: list[dict] = []
    emitted_until = start_seconds
    for index in np.argsort(starts, kind="stable"):
        window = windows[index]
        window_start = float(starts[index])
        window_times = window_start + (
            np.arange(window.shape[0], dtype=np.float64) / MODEL_SAMPLING_RATE
        )
        begin_time = max(emitted_until, start_seconds)
        begin = int(np.searchsorted(window_times, begin_time, side="left"))
        finish = int(np.searchsorted(window_times, end_seconds, side="left"))
        if finish <= begin:
            continue
        selected_windows.append(window[begin:finish])
        selected_times = window_times[begin:finish]
        timestamps.append(selected_times)
        segment_start = float(selected_times[0])
        segment_end = float(selected_times[-1] + 1 / MODEL_SAMPLING_RATE)
        if segments and segment_start <= segments[-1]["source_end_seconds"]:
            segments[-1]["source_end_seconds"] = max(segments[-1]["source_end_seconds"], segment_end)
        else:
            segments.append({
                "source_start_seconds": segment_start,
                "source_end_seconds": segment_end,
            })
        emitted_until = segment_end
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
        "time_seconds": [float(value) for value in time_values],
        "segments": segments,
    }


def _downsample(samples: np.ndarray, times: np.ndarray, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Downsample all channels using one shared index array."""

    if len(times) <= max_points:
        return samples, times
    indexes = np.linspace(0, len(times) - 1, max_points, dtype=np.int64)
    return samples[:, indexes], times[indexes]
