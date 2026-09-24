"""Create model-ready seizure-inference windows from private EEG data."""

from pathlib import Path

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


def validate_model_windows(windows: np.ndarray, window_starts: np.ndarray) -> None:
    """Validate the shared finite float32 model-input contract."""

    if windows.ndim != 3 or windows.shape[1:] != (WINDOW_SAMPLES, len(MODEL_CHANNELS)):
        raise ValueError("Model input must have shape (N, 1024, 18).")
    if windows.dtype != np.float32:
        raise ValueError("Model input must use float32 values.")
    if not np.isfinite(windows).all():
        raise ValueError("Model input must contain only finite values.")
    starts = np.asarray(window_starts)
    if starts.ndim != 1 or len(starts) != len(windows) or not np.isfinite(starts).all():
        raise ValueError("Model window starts must contain one finite value per window.")


def prepare_model_windows(
    processed_signals: np.ndarray,
    sampling_rate: int,
    channel_labels: list[str],
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return the exact model tensor from preprocessed EEG signals.

    Parameters use the preprocessing convention ``(channels, samples)``.
    The returned ``model_windows`` has the model convention
    ``(windows, time_steps, channels)`` and dtype ``float32``. Each row is a
    batch item of four seconds: ``(1024, 18)``. Windows start every two
    seconds to match the training notebook's 50% overlap. Partial trailing
    windows are not sent to inference and their sample count is returned
    separately.
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

    if selected.shape[1] < WINDOW_SAMPLES:
        raise ValueError("EEG is shorter than one required 4-second model window.")
    window_count = 1 + (selected.shape[1] - WINDOW_SAMPLES) // WINDOW_STEP_SAMPLES

    starts = np.arange(window_count, dtype=np.int64) * WINDOW_STEP_SAMPLES
    # channels × samples -> windows × channels × time -> windows × time × channels
    windows = np.stack(
        [selected[:, start : start + WINDOW_SAMPLES] for start in starts],
        axis=0,
    ).transpose(0, 2, 1).astype(np.float32, copy=False)
    validate_model_windows(windows, starts.astype(np.float32))
    last_end = int(starts[-1] + WINDOW_SAMPLES)
    discarded_tail_samples = selected.shape[1] - last_end
    window_start_seconds = (
        starts.astype(np.float32) / MODEL_SAMPLING_RATE
    )
    return windows, window_start_seconds, discarded_tail_samples


def preprocess_eeg(eeg_path: str | Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Read EDF or Nicolet input once and return model-ready tensors.

    The returned arrays are ``model_windows`` (N × 1024 × 18 float32) and
    ``window_start_seconds``. Keeping them in memory avoids writing a large
    transient NPZ only to reopen it in the next pipeline stage.
    """
    signals, sampling_rate, channel_labels = read_uniform_eeg(eeg_path)
    processed = EEGPreprocessor(sampling_rate=sampling_rate).preprocess(signals)
    model_windows, window_start_seconds, discarded_tail_samples = prepare_model_windows(
        processed, sampling_rate, channel_labels
    )

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
