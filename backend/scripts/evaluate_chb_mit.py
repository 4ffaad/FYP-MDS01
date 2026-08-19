"""Report aggregate CHB-MIT brainprint leakage and optional private H5 utility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from backend.app.core.config import TEMPLATE_KEY_ENV
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.model_input import prepare_model_windows
from backend.app.eeg.preprocessing import EEGPreprocessor
from backend.app.ml.h5_inference import H5InferenceService
from backend.app.privacy.crypto import read_base64_key
from backend.app.privacy.signal_projection import TRANSFORMATION_VERSION, cancellable_signal_projection
from backend.app.privacy.template import psd_features
from backend.app.research.chb_mit import SUBJECTS, recording_test_names, seizure_intervals, seizure_window_labels, sidecar_path


RANDOM_SEED = 42


def _exclusion_reason(exc: Exception) -> str:
    """Return an aggregate-safe incompatibility category without a source path."""

    message = str(exc).lower()
    if "sampling" in message or "256 hz" in message:
        return "sampling-rate mismatch"
    if "required channels" in message:
        return "montage mismatch"
    if "shorter than one required" in message:
        return "recording shorter than one model window"
    if "seizure annotation" in message:
        return "invalid seizure annotations"
    return f"unreadable or incompatible EDF ({type(exc).__name__})"


def _attack_metrics(features: np.ndarray, people: list[str], recordings: list[str]) -> dict:
    """Train a recording-held-out patient-ID attacker and return aggregate metrics."""

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("Install backend/requirements-research.txt first.") from exc
    held_out = {
        record
        for person in sorted(set(people))
        for record in recording_test_names([Path(item) for item, owner in zip(recordings, people) if owner == person])
    }
    test_mask = np.asarray([Path(record).name in held_out for record in recordings])
    if not test_mask.any() or (~test_mask).sum() == 0:
        raise RuntimeError("At least two recordings per subject are required for the identity attack.")
    classifier = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED),
    )
    labels = np.asarray(people)
    classifier.fit(features[~test_mask], labels[~test_mask])
    predicted = classifier.predict(features[test_mask])
    return {
        "top1_accuracy": float(accuracy_score(labels[test_mask], predicted)),
        "macro_f1": float(f1_score(labels[test_mask], predicted, average="macro", zero_division=0)),
        "test_windows": int(test_mask.sum()),
    }


def _update_h5_counts(
    service: H5InferenceService,
    windows: np.ndarray,
    starts: np.ndarray,
    labels: np.ndarray,
    counts: dict[str, int],
) -> None:
    """Accumulate one representation's H5 confusion-matrix counts."""

    predictions = service.predict(windows, starts, "CHB-MIT-EVALUATION")
    predicted = np.asarray([item.seizure_detected for item in predictions])
    counts["true_positive"] += int(np.sum(predicted & (labels == 1)))
    counts["false_negative"] += int(np.sum((~predicted) & (labels == 1)))
    counts["true_negative"] += int(np.sum((~predicted) & (labels == 0)))
    counts["false_positive"] += int(np.sum(predicted & (labels == 0)))


def _h5_utility(counts: dict[str, int]) -> dict:
    """Return aggregate seizure utility from private per-recording counts."""

    true_positive = counts["true_positive"]
    false_negative = counts["false_negative"]
    true_negative = counts["true_negative"]
    false_positive = counts["false_positive"]
    return {
        "sensitivity": true_positive / (true_positive + false_negative) if true_positive + false_negative else None,
        "specificity": true_negative / (true_negative + false_positive) if true_negative + false_positive else None,
        "positive_windows": true_positive + false_negative,
        "negative_windows": true_negative + false_positive,
    }


def evaluate(dataset_root: Path, model_path: Path | None = None, contract_path: Path | None = None) -> dict:
    """Compare control and shared transformed data without writing individual signals."""

    key = read_base64_key(TEMPLATE_KEY_ENV)
    controls: list[np.ndarray] = []
    transformed_features: list[np.ndarray] = []
    people: list[str] = []
    recordings: list[str] = []
    exclusion_counts: dict[str, int] = {}
    record_count = 0
    h5_service = H5InferenceService(model_path, contract_path) if model_path and contract_path else None
    h5_control_counts = {"true_positive": 0, "false_negative": 0, "true_negative": 0, "false_positive": 0}
    h5_transformed_counts = {"true_positive": 0, "false_negative": 0, "true_negative": 0, "false_positive": 0}
    for subject in SUBJECTS:
        subject_dir = dataset_root / subject
        for edf_path in sorted(subject_dir.glob("*.edf")):
            try:
                signals, sampling_rate, channel_labels = read_uniform_edf(edf_path)
                processed = EEGPreprocessor(sampling_rate=sampling_rate).preprocess(signals)
                windows, starts, _ = prepare_model_windows(processed, sampling_rate, channel_labels)
                transformed_windows = cancellable_signal_projection(windows, key)
                control = psd_features(windows)
                transformed = psd_features(transformed_windows)
                intervals = seizure_intervals(sidecar_path(edf_path))
            except Exception as exc:
                reason = _exclusion_reason(exc)
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
                continue
            record_count += 1
            controls.append(control)
            transformed_features.append(transformed)
            labels = np.asarray(seizure_window_labels(starts.tolist(), intervals), dtype=np.int8)
            if h5_service is not None:
                _update_h5_counts(h5_service, windows, starts, labels, h5_control_counts)
                _update_h5_counts(h5_service, transformed_windows, starts, labels, h5_transformed_counts)
            people.extend([subject] * len(windows))
            recordings.extend([f"{subject}/{edf_path.name}"] * len(windows))
    if not controls:
        raise RuntimeError("No compatible CHB-MIT recordings were found.")
    control_features = np.vstack(controls)
    transformed_feature_matrix = np.vstack(transformed_features)
    report = {
        "research_only": True,
        "subjects": list(SUBJECTS),
        "random_seed": RANDOM_SEED,
        "subject_count": len(set(people)),
        "recordings": record_count,
        "windows": int(len(control_features)),
        "chance_top1_accuracy": 1 / len(set(people)),
        "exclusions": [
            {"reason": reason, "count": count}
            for reason, count in sorted(exclusion_counts.items())
        ],
        "identity_attack": {
            "control_psd": _attack_metrics(control_features, people, recordings),
            "cancellable_signal_projection": _attack_metrics(transformed_feature_matrix, people, recordings),
            "transformation_version": TRANSFORMATION_VERSION,
        },
        "seizure_utility": None,
    }
    if h5_service is not None:
        report["seizure_utility"] = {
            "control": _h5_utility(h5_control_counts),
            "cancellable_signal_projection": _h5_utility(h5_transformed_counts),
        }
        report["seizure_utility_note"] = "Both detector results and identity attacks use their matching representation. This evaluates utility loss; it does not establish clinical validity."
    return report


def main() -> None:
    """Write one aggregate-only JSON report for the fixed CHB-MIT study."""

    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    if bool(args.model) != bool(args.contract):
        raise SystemExit("--model and --contract must be supplied together.")
    args.output.write_text(json.dumps(evaluate(args.dataset_root, args.model, args.contract), indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
