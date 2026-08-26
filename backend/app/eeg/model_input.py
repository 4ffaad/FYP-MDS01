"""Create model-ready seizure-inference windows from private EDF data."""

from pathlib import Path

import numpy as np

from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.preprocessing import EEGPreprocessor


# This order is part of the trained model contract. Do not sort, replace, or
# infer channel positions: a correct shape with incorrect labels is invalid.
MODEL_CHANNELS = (
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1", "FP1-F3", "F3-C3",
    "C3-P3", "P3-O1", "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
    "FP2-F8", "F8-T8", "T8-P8", "P8-O2", "FZ-CZ", "CZ-PZ",
)
MODEL_SAMPLING_RATE = 256
WINDOW_SECONDS = 4
WINDOW_SAMPLES = MODEL_SAMPLING_RATE * WINDOW_SECONDS
WINDOW_STEP_SECONDS = 2
WINDOW_STEP_SAMPLES = MODEL_SAMPLING_RATE * WINDOW_STEP_SECONDS


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

    label_to_index = {label.strip(): index for index, label in enumerate(channel_labels)}
    missing_channels = [label for label in MODEL_CHANNELS if label not in label_to_index]
    if missing_channels:
        raise ValueError(
            "EDF does not contain the model's required channels: "
            + ", ".join(missing_channels)
        )

    selected = processed_signals[[label_to_index[label] for label in MODEL_CHANNELS]]
    if WINDOW_STEP_SAMPLES <= 0 or WINDOW_STEP_SAMPLES > WINDOW_SAMPLES:
        raise ValueError("Model window stride must be positive and no larger than the window.")

    if selected.shape[1] < WINDOW_SAMPLES:
        raise ValueError("EDF is shorter than one required 4-second model window.")
    window_count = 1 + (selected.shape[1] - WINDOW_SAMPLES) // WINDOW_STEP_SAMPLES

    starts = np.arange(window_count, dtype=np.int64) * WINDOW_STEP_SAMPLES
    # channels × samples -> windows × channels × time -> windows × time × channels
    windows = np.stack(
        [selected[:, start : start + WINDOW_SAMPLES] for start in starts],
        axis=0,
    ).transpose(0, 2, 1).astype(np.float32, copy=False)
    last_end = int(starts[-1] + WINDOW_SAMPLES)
    discarded_tail_samples = selected.shape[1] - last_end
    window_start_seconds = (
        starts.astype(np.float32) / MODEL_SAMPLING_RATE
    )
    return windows, window_start_seconds, discarded_tail_samples


def preprocess_edf(edf_path: str | Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Read an EDF once and return its model-ready tensor in memory.

    The returned arrays are ``model_windows`` (N × 1024 × 18 float32) and
    ``window_start_seconds``. Keeping them in memory avoids writing a large
    transient NPZ only to reopen it in the next pipeline stage.
    """
    signals, sampling_rate, channel_labels = read_uniform_edf(edf_path)
    processed = EEGPreprocessor(sampling_rate=sampling_rate).preprocess(signals)
    model_windows, window_start_seconds, discarded_tail_samples = prepare_model_windows(
        processed, sampling_rate, channel_labels
    )

    return model_windows, window_start_seconds, {
        "sampling_rate": sampling_rate,
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
