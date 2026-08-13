"""Create model-ready seizure-inference windows from de-identified EDF data."""

from pathlib import Path

import numpy as np

from app.core.config import PROCESSED_DIR, ensure_storage_directories
from app.services.edf_io import read_uniform_edf
from app.services.eeg_preprocessor import EEGPreprocessor


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


def prepare_model_windows(
    processed_signals: np.ndarray,
    sampling_rate: int,
    channel_labels: list[str],
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return the exact model tensor from preprocessed EEG signals.

    Parameters use the preprocessing convention ``(channels, samples)``.
    The returned ``model_windows`` has the model convention
    ``(windows, time_steps, channels)`` and dtype ``float32``. Each row is a
    batch item of four seconds: ``(1024, 18)``. Partial trailing windows are
    not sent to inference and their sample count is returned separately.
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
    window_count = selected.shape[1] // WINDOW_SAMPLES
    if window_count == 0:
        raise ValueError("EDF is shorter than one required 4-second model window.")

    usable_samples = window_count * WINDOW_SAMPLES
    discarded_tail_samples = selected.shape[1] - usable_samples
    # channels × samples -> channels × windows × time -> windows × time × channels
    windows = selected[:, :usable_samples].reshape(
        len(MODEL_CHANNELS), window_count, WINDOW_SAMPLES
    ).transpose(1, 2, 0).astype(np.float32, copy=False)
    window_start_seconds = (
        np.arange(window_count, dtype=np.float32) * WINDOW_SECONDS
    )
    return windows, window_start_seconds, discarded_tail_samples


def preprocess_edf_to_npz(edf_path: str | Path, record_id: str) -> tuple[Path, dict]:
    """Apply the project pipeline and save the trained model's input tensor.

    The output name comes from ``record_id``, never a client filename. Its NPZ
    arrays are ``model_windows`` (N × 1024 × 18 float32),
    ``window_start_seconds``, ``sampling_rate`` and ``channel_labels``. A model
    can pass all N windows to ``model.predict`` in one batch, or one window as
    ``model_windows[index:index + 1]``.
    """
    ensure_storage_directories()
    signals, sampling_rate, channel_labels = read_uniform_edf(edf_path)
    processed = EEGPreprocessor(sampling_rate=sampling_rate).preprocess(signals)
    model_windows, window_start_seconds, discarded_tail_samples = prepare_model_windows(
        processed, sampling_rate, channel_labels
    )

    output_path = PROCESSED_DIR / f"{record_id}.npz"
    np.savez_compressed(
        output_path,
        model_windows=model_windows,
        window_start_seconds=window_start_seconds,
        sampling_rate=sampling_rate,
        channel_labels=np.asarray(MODEL_CHANNELS),
    )
    return output_path, {
        "sampling_rate": sampling_rate,
        "source_channel_count": len(channel_labels),
        "original_shape": list(signals.shape),
        "processed_shape": list(processed.shape),
        "model_input_shape": list(model_windows.shape),
        "model_window_count": int(model_windows.shape[0]),
        "model_window_seconds": WINDOW_SECONDS,
        "model_channel_count": len(MODEL_CHANNELS),
        "discarded_tail_samples": discarded_tail_samples,
        "preprocessing": {
            "bandpass": "0.5-100 Hz",
            "notch": "60 Hz",
            "normalization": "z-score per channel",
            "artifact_clipping": "±5",
        },
    }
