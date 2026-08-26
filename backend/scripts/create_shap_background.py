"""Create private, profile-specific SHAP background tensors from CHB-MIT."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import numpy as np

from backend.app.eeg.model_input import MODEL_CHANNELS, WINDOW_SAMPLES
from backend.app.eeg.model_input import preprocess_edf
from backend.app.core.config import TEMPLATE_KEY_ENV
from backend.app.privacy.crypto import read_base64_key
from backend.app.privacy.deidentify import deidentify_edf
from backend.app.privacy.signal_projection import obfuscate_signal
from backend.app.research.chb_mit import seizure_window_labels
from backend.app.research.evaluation import EVALUATION_SPLITS, discover_chb_mit


BACKGROUND_WINDOWS = 32
MAX_WINDOWS_PER_RECORDING = 8
TEMPORARY_RECORD_ID = "SHAP-BACKGROUND"


def _select_non_seizure_windows(
    windows: np.ndarray,
    starts: np.ndarray,
    intervals: list[tuple[float, float]],
) -> np.ndarray:
    """Select a bounded, evenly spaced set of reference-negative windows."""

    labels = np.asarray(seizure_window_labels(starts.tolist(), intervals), dtype=np.int8)
    eligible = np.flatnonzero(labels == 0)
    if not len(eligible):
        return np.empty((0, WINDOW_SAMPLES, len(MODEL_CHANNELS)), dtype=np.float32)
    selected_count = min(MAX_WINDOWS_PER_RECORDING, len(eligible))
    selected_positions = np.linspace(0, len(eligible) - 1, selected_count, dtype=np.int64)
    return windows[eligible[selected_positions]].astype(np.float32, copy=False)


def _collect_candidates(dataset_root: Path) -> tuple[np.ndarray, int]:
    """Build bounded metadata-scrubbed candidates from chb07 and chb08."""

    recordings, discovery_exclusions = discover_chb_mit(dataset_root)
    calibration_subjects = set(EVALUATION_SPLITS["calibration"])
    selected = [item for item in recordings if item.subject_id in calibration_subjects]
    if not selected:
        raise ValueError("No calibration recordings were found for chb07 and chb08.")

    candidates: list[np.ndarray] = []
    processing_exclusions = len(discovery_exclusions)
    for recording in selected:
        try:
            with tempfile.TemporaryDirectory(prefix="mds01-shap-") as directory:
                scrubbed_path = Path(directory) / "scrubbed.edf"
                deidentify_edf(recording.path, scrubbed_path, TEMPORARY_RECORD_ID)
                windows, starts, _details = preprocess_edf(scrubbed_path)
                selected_windows = _select_non_seizure_windows(
                    windows,
                    starts,
                    list(recording.intervals),
                )
                if len(selected_windows):
                    candidates.append(selected_windows)
        except Exception:
            # This is an offline background-building utility. One incompatible
            # calibration recording must not make a valid sibling unusable.
            processing_exclusions += 1

    if not candidates:
        raise ValueError("No compatible non-seizure calibration windows were found.")
    return np.concatenate(candidates, axis=0), processing_exclusions


def _choose_background(candidates: np.ndarray) -> np.ndarray:
    """Choose exactly 32 deterministic windows with the model input contract."""

    if candidates.ndim != 3 or candidates.shape[1:] != (WINDOW_SAMPLES, len(MODEL_CHANNELS)):
        raise ValueError("Candidate windows do not match the (N, 1024, 18) contract.")
    if len(candidates) < BACKGROUND_WINDOWS:
        raise ValueError(
            f"Need at least {BACKGROUND_WINDOWS} suitable calibration windows; found {len(candidates)}."
        )
    positions = np.linspace(0, len(candidates) - 1, BACKGROUND_WINDOWS, dtype=np.int64)
    selected = candidates[positions].astype(np.float32, copy=True)
    _validate_background(selected)
    return selected


def _validate_background(background: np.ndarray) -> None:
    """Reject background data that cannot be safely passed to SHAP."""

    expected_shape = (BACKGROUND_WINDOWS, WINDOW_SAMPLES, len(MODEL_CHANNELS))
    if background.shape != expected_shape or background.dtype != np.float32:
        raise ValueError("SHAP background must have shape (32, 1024, 18) and dtype float32.")
    if not np.isfinite(background).all():
        raise ValueError("SHAP background must contain only finite values.")


def _write_background(path: Path, background: np.ndarray) -> None:
    """Write one validated private background tensor as a NumPy file."""

    _validate_background(background)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, background, allow_pickle=False)


def create_backgrounds(dataset_root: Path, output_dir: Path) -> dict[str, int]:
    """Create metadata-scrubbed and obfuscated SHAP backgrounds.

    Parameters
    ----------
    dataset_root : pathlib.Path
        CHB-MIT directory containing the subject folders.
    output_dir : pathlib.Path
        Private directory for the generated `.npy` files.

    Returns
    -------
    dict[str, int]
        Counts of candidate windows and skipped recordings.

    Raises
    ------
    ValueError
        Raised when the calibration set has fewer than 32 compatible windows.
    CryptoError
        Raised when the template key is missing or invalid.

    Privacy
    -------
    The output contains EEG-derived model inputs. It must remain private,
    ignored by Git, and must never be returned by an API endpoint.
    """

    candidates, exclusions = _collect_candidates(dataset_root)
    metadata_background = _choose_background(candidates)
    template_key = read_base64_key(TEMPLATE_KEY_ENV)
    obfuscated_background = obfuscate_signal(metadata_background, template_key)
    _validate_background(obfuscated_background)

    _write_background(output_dir / "shap-background-metadata.npy", metadata_background)
    _write_background(output_dir / "shap-background-obfuscated.npy", obfuscated_background)
    return {"candidate_windows": len(candidates), "skipped_recordings": exclusions}


def main() -> int:
    """Parse paths, generate both backgrounds, and print aggregate counts."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path, help="CHB-MIT dataset directory.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/model"),
        help="Private output directory for the two background tensors.",
    )
    args = parser.parse_args()
    summary = create_backgrounds(args.dataset_root, args.output_dir)
    print(f"Wrote 32-window SHAP backgrounds to {args.output_dir}")
    print(f"Candidate windows: {summary['candidate_windows']}")
    print(f"Skipped recordings: {summary['skipped_recordings']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
