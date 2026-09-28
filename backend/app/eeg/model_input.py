"""Create model-ready seizure-inference windows from private EEG data."""

from collections.abc import Sequence
from pathlib import Path
import math

import numpy as np

from backend.app.eeg.contracts import MODEL_CHANNELS, MODEL_SAMPLING_RATE
from backend.app.eeg.io import read_uniform_eeg
from backend.app.eeg.preprocessing import EEGPreprocessor


# This order is part of the trained model contract. Do not sort, replace, or
# infer channel positions: a correct shape with incorrect labels is invalid.
WINDOW_SECONDS = 4
WINDOW_SAMPLES = MODEL_SAMPLING_RATE * WINDOW_SECONDS
WINDOW_STEP_SECONDS = 2
WINDOW_STEP_SAMPLES = MODEL_SAMPLING_RATE * WINDOW_STEP_SECONDS
SegmentLayoutEntry = tuple[int, int, float] | tuple[int, int, float, float]


def validate_model_time_offsets(window_starts: np.ndarray | Sequence[float]) -> np.ndarray:
    """Reject offsets whose float spacing cannot represent every sample."""

    raw_starts = np.asarray(window_starts)
    if raw_starts.ndim != 1 or not np.issubdtype(raw_starts.dtype, np.number):
        raise ValueError("Model timestamps must be a one-dimensional numeric array.")
    if not np.isfinite(raw_starts).all():
        raise ValueError("Model timestamps must be finite.")
    float64_starts = raw_starts.astype(np.float64, copy=False)
    if not np.isfinite(float64_starts).all():
        raise ValueError("Model timestamps must be finite float64 values.")
    with np.errstate(over="ignore", invalid="ignore"):
        precision = np.spacing(np.abs(float64_starts))
        if np.issubdtype(raw_starts.dtype, np.floating):
            precision = np.maximum(precision, np.spacing(np.abs(raw_starts)))
    if np.any(precision >= 1.0 / MODEL_SAMPLING_RATE):
        raise ValueError("Model timestamp precision is insufficient for the sample grid.")
    return float64_starts



def validate_model_windows(windows: np.ndarray, window_starts: np.ndarray) -> None:
    """Validate the shared finite float32 model-input contract."""

    if windows.ndim != 3 or windows.shape[1:] != (WINDOW_SAMPLES, len(MODEL_CHANNELS)):
        raise ValueError("Model input must have shape (N, 1024, 18).")
    if windows.dtype != np.float32:
        raise ValueError("Model input must use float32 values.")
    if not np.isfinite(windows).all():
        raise ValueError("Model input must contain only finite values.")
    starts = validate_model_time_offsets(window_starts)
    if len(starts) != len(windows):
        raise ValueError("Model window starts must contain one finite value per window.")


def _validated_segment_layout(
    segments: Sequence[SegmentLayoutEntry] | None,
    total_samples: int,
) -> list[tuple[int, int, float, float]]:
    """Validate sample ranges and cumulative source-time segment order.

    Four-item entries may provide the exact source duration when resampling
    rounded a segment's model sample count upward.
    """

    selected_segments = (
        list(segments)
        if segments is not None
        else [(0, total_samples, 0.0, total_samples / MODEL_SAMPLING_RATE)]
    )
    if not selected_segments:
        raise ValueError("EEG does not contain a full 4-second model window.")

    validated: list[tuple[int, int, float, float]] = []
    expected_sample_start = 0
    expected_segment_end: float | None = None
    timing_tolerance = max(1e-6, 0.5 / MODEL_SAMPLING_RATE)
    for segment in selected_segments:
        if not isinstance(segment, (list, tuple)) or len(segment) not in {3, 4}:
            raise ValueError("EEG segment sample ranges or start times are invalid.")
        sample_start = segment[0]
        sample_count = segment[1]
        segment_start_seconds = segment[2]
        if (
            isinstance(sample_start, bool)
            or not isinstance(sample_start, int)
            or isinstance(sample_count, bool)
            or not isinstance(sample_count, int)
            or sample_count <= 0
            or sample_start != expected_sample_start
            or sample_start + sample_count > total_samples
            or isinstance(segment_start_seconds, bool)
            or not isinstance(segment_start_seconds, (int, float))
            or not math.isfinite(segment_start_seconds)
            or segment_start_seconds < 0
        ):
            raise ValueError("EEG segment sample ranges or start times are invalid.")
        segment_duration_seconds = (
            segment[3] if len(segment) == 4 else sample_count / MODEL_SAMPLING_RATE
        )
        if (
            isinstance(segment_duration_seconds, bool)
            or not isinstance(segment_duration_seconds, (int, float))
            or not math.isfinite(segment_duration_seconds)
            or segment_duration_seconds <= 0
        ):
            raise ValueError("EEG segment sample ranges or start times are invalid.")
        segment_start_seconds = float(segment_start_seconds)
        validate_model_time_offsets([segment_start_seconds])
        if expected_segment_end is not None:
            if segment_start_seconds < expected_segment_end - timing_tolerance:
                raise ValueError("EEG segment start times overlap.")
            if segment_start_seconds > expected_segment_end + timing_tolerance:
                expected_segment_end = segment_start_seconds
        else:
            expected_segment_end = segment_start_seconds
        expected_segment_end += float(segment_duration_seconds)
        validate_model_time_offsets([expected_segment_end])
        validated.append(
            (
                sample_start,
                sample_count,
                segment_start_seconds,
                float(segment_duration_seconds),
            )
        )
        expected_sample_start += sample_count
    if expected_sample_start != total_samples:
        raise ValueError("EEG segment sample ranges do not cover the signal.")
    return validated


def _coalesce_contiguous_segments(
    segments: Sequence[tuple[int, int, float, float]],
) -> list[tuple[int, int, float, float]]:
    """Join only sample-adjacent segments whose source times have no gap."""

    coalesced: list[tuple[int, int, float, float]] = []
    timing_tolerance = max(1e-6, 0.5 / MODEL_SAMPLING_RATE)
    for sample_start, sample_count, start_seconds, duration_seconds in segments:
        if not coalesced:
            coalesced.append((sample_start, sample_count, start_seconds, duration_seconds))
            continue
        previous_start, previous_count, previous_time, previous_duration = coalesced[-1]
        source_gap = start_seconds - (previous_time + previous_duration)
        if source_gap > timing_tolerance:
            coalesced.append((sample_start, sample_count, start_seconds, duration_seconds))
            continue
        if source_gap < -timing_tolerance:
            raise ValueError("EEG segment start times overlap.")
        coalesced[-1] = (
            previous_start,
            previous_count + sample_count,
            previous_time,
            start_seconds + duration_seconds - previous_time,
        )
    return coalesced


def prepare_model_windows(
    processed_signals: np.ndarray,
    sampling_rate: int,
    channel_labels: list[str],
    segments: Sequence[SegmentLayoutEntry] | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return the exact model tensor from preprocessed EEG signals.

    Parameters use the preprocessing convention ``(channels, samples)``.
    The returned ``model_windows`` has the model convention
    ``(windows, time_steps, channels)`` and dtype ``float32``. Each row is a
    batch item of four seconds: ``(1024, 18)``. Windows start every two
    seconds to match the training notebook's 50% overlap. Partial trailing
    windows are not sent to inference and their sample count is returned
    separately.

    ``segments`` optionally maps concatenated sample ranges to source-relative
    starts as ``(sample_start, sample_count, start_seconds)``. A fourth
    ``duration_seconds`` value preserves source timing when resampling rounds a
    segment's model sample count upward. Time-contiguous ranges are coalesced
    before filtering and windowing; known gaps remain independent.
    """
    if sampling_rate != MODEL_SAMPLING_RATE:
        raise ValueError(
            f"Model requires {MODEL_SAMPLING_RATE} Hz EEG; received {sampling_rate} Hz."
        )

    if processed_signals.ndim != 2 or processed_signals.shape[0] != len(channel_labels):
        raise ValueError("EEG signal data does not match its channel labels.")
    if not np.isfinite(processed_signals).all():
        raise ValueError("EEG signal contains non-finite values.")

    normalized_labels = [label.strip() for label in channel_labels]
    if len(normalized_labels) != len(set(normalized_labels)):
        raise ValueError("EEG contains duplicate channel labels.")
    if len(normalized_labels) != len(MODEL_CHANNELS) or set(normalized_labels) != set(MODEL_CHANNELS):
        raise ValueError("EEG must contain exactly the model's required channels.")
    label_to_index = {label: index for index, label in enumerate(normalized_labels)}
    missing_channels = [label for label in MODEL_CHANNELS if label not in label_to_index]
    if missing_channels:
        raise ValueError(
            "EEG does not contain the model's required channels: "
            + ", ".join(missing_channels)
        )

    selected = processed_signals[[label_to_index[label] for label in MODEL_CHANNELS]]
    if WINDOW_STEP_SAMPLES <= 0 or WINDOW_STEP_SAMPLES > WINDOW_SAMPLES:
        raise ValueError("Model window stride must be positive and no larger than the window.")

    selected_segments = _coalesce_contiguous_segments(
        _validated_segment_layout(segments, selected.shape[1])
    )

    prepared_segments: list[tuple[int, int, float, int]] = []
    discarded_tail_samples = 0
    for sample_start, sample_count, segment_start_seconds, duration_seconds in selected_segments:
        if sample_count < WINDOW_SAMPLES:
            discarded_tail_samples += sample_count
        else:
            sample_window_count = 1 + (sample_count - WINDOW_SAMPLES) // WINDOW_STEP_SAMPLES
            timeline_window_count = max(
                0,
                1
                + math.floor(
                    (duration_seconds - WINDOW_SECONDS) / WINDOW_STEP_SECONDS
                ),
            )
            window_count = min(sample_window_count, timeline_window_count)
            if window_count == 0:
                discarded_tail_samples += sample_count
                continue
            prepared_segments.append(
                (sample_start, sample_count, segment_start_seconds, window_count)
            )
            last_start = (window_count - 1) * WINDOW_STEP_SAMPLES
            last_end = last_start + WINDOW_SAMPLES
            discarded_tail_samples += sample_count - last_end

    total_windows = sum(window_count for *_segment, window_count in prepared_segments)
    if total_windows == 0:
        raise ValueError("EEG is shorter than one required 4-second model window.")
    model_windows = np.empty(
        (total_windows, WINDOW_SAMPLES, len(MODEL_CHANNELS)),
        dtype=np.float32,
    )
    window_start_seconds = np.empty(total_windows, dtype=np.float64)
    window_cursor = 0
    for sample_start, sample_count, segment_start_seconds, window_count in prepared_segments:
        segment_signals = selected[:, sample_start : sample_start + sample_count]
        all_windows = np.lib.stride_tricks.sliding_window_view(
            segment_signals,
            window_shape=WINDOW_SAMPLES,
            axis=1,
        )
        segment_windows = all_windows[:, ::WINDOW_STEP_SAMPLES, :][:, :window_count, :]
        window_end = window_cursor + window_count
        model_windows[window_cursor:window_end] = segment_windows.transpose(1, 2, 0)
        segment_starts = (
            segment_start_seconds
            + np.arange(window_count, dtype=np.float64)
            * WINDOW_STEP_SECONDS
        )
        window_start_seconds[window_cursor:window_end] = segment_starts
        window_cursor = window_end
    validate_model_windows(model_windows, window_start_seconds)
    return model_windows, window_start_seconds, discarded_tail_samples


def preprocess_eeg(
    eeg_path: str | Path,
    *,
    segments: Sequence[SegmentLayoutEntry] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Read EDF or Nicolet input once and return model-ready tensors.

    The returned arrays are ``model_windows`` (N × 1024 × 18 float32) and
    ``window_start_seconds``. Keeping them in memory avoids writing a large
    transient NPZ only to reopen it in the next pipeline stage.

    Segments shorter than one complete model window cannot contribute an
    inference window, so they are excluded before filtering and normalization.
    Remaining segments retain their source-relative start times.
    """
    signals, sampling_rate, channel_labels = read_uniform_eeg(eeg_path)
    preprocessor = EEGPreprocessor(sampling_rate=sampling_rate)
    segment_layout = (
        _coalesce_contiguous_segments(_validated_segment_layout(segments, signals.shape[1]))
        if segments is not None
        else None
    )
    discarded_short_segment_count = 0
    discarded_short_segment_samples = 0
    if segment_layout is None:
        processed = preprocessor.preprocess(signals)
    else:
        processable_segments = []
        for sample_start, sample_count, _start_seconds, _duration_seconds in segment_layout:
            if sample_count < WINDOW_SAMPLES:
                discarded_short_segment_count += 1
                discarded_short_segment_samples += sample_count
                continue
            processable_segments.append(
                (sample_start, sample_count, _start_seconds, _duration_seconds)
            )
        if not processable_segments:
            raise ValueError("EEG does not contain a full 4-second model window.")

        processed_segments: list[np.ndarray] = []
        processed_layout: list[tuple[int, int, float, float]] = []
        processed_sample_start = 0
        for sample_start, sample_count, start_seconds, duration_seconds in processable_segments:
            sample_end = sample_start + sample_count
            contiguous = signals[:, sample_start:sample_end]
            filtered = preprocessor.bandpass_filter(contiguous)
            processed_segments.append(preprocessor.notch_filter(filtered))
            processed_layout.append(
                (processed_sample_start, sample_count, start_seconds, duration_seconds)
            )
            processed_sample_start += sample_count
        processed = np.concatenate(processed_segments, axis=1)
        processed = preprocessor.remove_artifacts(preprocessor.normalize(processed))
        if not np.isfinite(processed).all():
            raise ValueError("EEG preprocessing produced non-finite values.")
        segment_layout = processed_layout
    model_windows, window_start_seconds, discarded_tail_samples = prepare_model_windows(
        processed, sampling_rate, channel_labels, segments=segment_layout
    )
    discarded_tail_samples += discarded_short_segment_samples

    return model_windows, window_start_seconds, {
        "sampling_rate": sampling_rate,
        "source_format": Path(eeg_path).suffix.lower().lstrip("."),
        "source_channel_count": len(channel_labels),
        "original_shape": list(signals.shape),
        "processed_shape": list(processed.shape),
        "model_input_shape": list(model_windows.shape),
        "model_window_count": int(model_windows.shape[0]),
        "model_window_seconds": WINDOW_SECONDS,
        "model_window_step_seconds": WINDOW_STEP_SECONDS,
        "model_window_overlap": "50%",
        "model_channel_count": len(MODEL_CHANNELS),
        "discarded_tail_samples": discarded_tail_samples,
        "discarded_short_segment_count": discarded_short_segment_count,
        "discarded_short_segment_samples": discarded_short_segment_samples,
        "model_segment_count": len(segment_layout) if segment_layout is not None else 1,
        "preprocessing": {
            "bandpass": "0.5-100 Hz",
            "notch": "60 Hz",
            "normalization": "z-score per channel",
            "artifact_clipping": "±5",
        },
    }


def preprocess_edf(edf_path: str | Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Backward-compatible EDF preprocessing wrapper."""

    return preprocess_eeg(edf_path)
