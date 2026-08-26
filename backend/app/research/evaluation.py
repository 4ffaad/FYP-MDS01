"""Patient-disjoint CHB-MIT evaluation for seizure utility reports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Any

import numpy as np

from backend.app.core.config import H5_CONTRACT_PATH, H5_MODEL_PATH, TEMPLATE_KEY_ENV
from backend.app.eeg.model_input import preprocess_edf
from backend.app.ml.h5_inference import H5InferenceService
from backend.app.privacy.deidentify import deidentify_edf
from backend.app.privacy.methods import CANONICAL_COMBINED, METADATA_SCRUB, SIGNAL_OBFUSCATION
from backend.app.privacy.signal_projection import obfuscate_signal
from backend.app.privacy.crypto import read_base64_key
from backend.app.research.chb_mit import SUBJECTS, seizure_intervals, seizure_window_labels, sidecar_path
from backend.app.research.metrics import (
    calibration_metrics,
    classification_metrics,
    patient_bootstrap_f1,
    precision_recall_points,
    roc_points,
    threshold_sweep,
)


EVALUATION_SPLITS = {
    "train": tuple(SUBJECTS[:6]),
    "calibration": tuple(SUBJECTS[6:8]),
    "test": tuple(SUBJECTS[8:]),
}
SUBJECT_PATTERN = re.compile(r"^chb\d{2}$", re.IGNORECASE)


@dataclass(frozen=True)
class EvaluationRecording:
    """One CHB-MIT EDF and its optional research-only seizure intervals."""

    path: Path
    subject_id: str
    intervals: tuple[tuple[float, float], ...]


def split_subjects(subjects: list[str] | tuple[str, ...] = SUBJECTS) -> dict[str, tuple[str, ...]]:
    """Return the fixed patient-disjoint train/calibration/test manifest."""

    normalized = tuple(sorted({subject.lower() for subject in subjects if SUBJECT_PATTERN.fullmatch(subject)}))
    if normalized != tuple(SUBJECTS):
        raise ValueError("Evaluation requires the fixed chb01-chb10 subject manifest.")
    return {name: tuple(values) for name, values in EVALUATION_SPLITS.items()}


def discover_chb_mit(dataset_root: Path) -> tuple[list[EvaluationRecording], list[dict[str, str]]]:
    """Discover fixed-manifest CHB-MIT EDFs and parse optional sidecars.

    Returns
    -------
    tuple[list[EvaluationRecording], list[dict[str, str]]]
        Discovered recordings and aggregate-safe exclusions. Missing sidecars
        are represented by empty intervals; malformed sidecars are excluded.
    """

    if not dataset_root.is_dir():
        raise ValueError("CHB-MIT dataset root must be a directory.")
    recordings: list[EvaluationRecording] = []
    exclusions: list[dict[str, str]] = []
    allowed = set(SUBJECTS)
    for path in sorted(item for item in dataset_root.rglob("*") if item.is_file() and item.suffix.lower() == ".edf"):
        subject_id = next((part.lower() for part in path.parts if part.lower() in allowed), None)
        if subject_id is None:
            subject_match = re.search(r"(?:^|[_-])(chb\d{2})(?:[_-]|$)", path.stem.lower())
            if subject_match and subject_match.group(1) in allowed:
                subject_id = subject_match.group(1)
        if subject_id is None:
            exclusions.append({"reason": "recording is outside chb01-chb10 manifest"})
            continue
        try:
            intervals = tuple(seizure_intervals(sidecar_path(path)))
        except (OSError, ValueError):
            exclusions.append({"reason": "malformed optional seizure sidecar"})
            continue
        recordings.append(EvaluationRecording(path, subject_id, intervals))
    if not recordings:
        raise ValueError("No CHB-MIT EDF recordings were discovered for chb01-chb10.")
    return recordings, exclusions


def build_metrics_report(
    *,
    labels: list[int],
    scores: list[float],
    patient_ids: list[str],
    duration_hours: float,
    threshold: float,
    seed: int,
) -> dict[str, Any]:
    """Build accuracy, ranking, calibration, and patient-bootstrap metrics."""

    report: dict[str, Any] = {
        "classification": classification_metrics(labels, scores, threshold=threshold, duration_hours=duration_hours),
        "roc": roc_points(labels, scores),
        "precision_recall": precision_recall_points(labels, scores),
        "calibration": calibration_metrics(labels, scores),
        "threshold_sweep": threshold_sweep(labels, scores, [0.25, 0.35, 0.5, 0.65, 0.75]),
        "sklearn_available": False,
    }
    if len(set(patient_ids)) >= 2:
        report["patient_bootstrap_f1"] = patient_bootstrap_f1(
            labels,
            scores,
            patient_ids,
            threshold=threshold,
            seed=seed,
        )
    else:
        report["patient_bootstrap_f1"] = None

    try:
        from sklearn.metrics import average_precision_score, roc_auc_score
        if len(set(labels)) == 2:
            report["roc_auc"] = float(roc_auc_score(labels, scores))
            report["average_precision"] = float(average_precision_score(labels, scores))
        else:
            report["roc_auc"] = None
            report["average_precision"] = None
    except ImportError:
        report["roc_auc"] = None
        report["average_precision"] = None
    else:
        report["sklearn_available"] = True
    return report


def evaluate_dataset(
    *,
    dataset_root: Path,
    privacy_method: str = METADATA_SCRUB,
    split: str = "test",
    seed: int = 0,
) -> dict[str, Any]:
    """Evaluate the reviewed H5 model on a fixed patient-disjoint split.

    Parameters
    ----------
    dataset_root : pathlib.Path
        Local CHB-MIT dataset directory. It is never copied into the report.
    privacy_method : str
        ``metadata-scrub`` or ``metadata-scrub+signal-obfuscation``. The
        baseline always scrubs metadata before preprocessing; obfuscation is
        applied only for the second evaluation profile. The legacy
        ``signal-obfuscation`` spelling is accepted as an input alias.
    split : str
        Fixed manifest split to evaluate, normally ``test``.
    seed : int
        Seed recorded for deterministic bootstrap sampling.
    """

    if privacy_method == SIGNAL_OBFUSCATION:
        privacy_method = CANONICAL_COMBINED
    if privacy_method not in {METADATA_SCRUB, CANONICAL_COMBINED}:
        raise ValueError("privacy_method must be metadata-scrub or metadata-scrub+signal-obfuscation.")
    manifest = split_subjects()
    if split not in manifest:
        raise ValueError("split must be train, calibration, or test.")
    recordings, discovery_exclusions = discover_chb_mit(dataset_root)
    selected = [item for item in recordings if item.subject_id in manifest[split]]
    if not selected:
        raise ValueError(f"No recordings found for the {split} split.")

    inference = H5InferenceService(H5_MODEL_PATH, H5_CONTRACT_PATH)
    obfuscate = privacy_method == CANONICAL_COMBINED
    template_key = read_base64_key(TEMPLATE_KEY_ENV) if obfuscate else None
    labels: list[int] = []
    scores: list[float] = []
    patient_ids: list[str] = []
    duration_hours = 0.0
    exclusions = list(discovery_exclusions)
    evaluated_recordings = 0

    for recording_index, recording in enumerate(selected):
        try:
            with tempfile.TemporaryDirectory(prefix="mds01-eval-") as directory:
                scrubbed_path = Path(directory) / "scrubbed.edf"
                deidentify_edf(recording.path, scrubbed_path, f"EVAL-{recording_index:04d}")
                windows, starts, details = preprocess_edf(scrubbed_path)
                if obfuscate:
                    windows = obfuscate_signal(windows, template_key or b"")
                predictions = inference.predict(windows, starts, f"EVAL-{recording_index:04d}")
                recording_labels = seizure_window_labels(starts.tolist(), list(recording.intervals))
                if len(recording_labels) != len(predictions):
                    raise ValueError("Evaluation label and prediction window counts differ.")
                labels.extend(recording_labels)
                scores.extend([item.probability for item in predictions])
                patient_ids.extend([recording.subject_id] * len(predictions))
                duration_hours += float(details["original_shape"][1]) / float(details["sampling_rate"]) / 3600
                evaluated_recordings += 1
        except Exception as exc:
            exclusions.append({"reason": _safe_reason(exc)})

    if not labels:
        raise ValueError("No compatible labelled recordings were evaluated.")
    return {
        "dataset": "CHB-MIT",
        "subjects": list(manifest[split]),
        "split": split,
        "privacy_method": privacy_method,
        "model": {
            "name": inference.model_name,
            "version": inference.model_version,
            "threshold": inference.threshold,
            "score_type": inference.score_type,
        },
        "seed": seed,
        "split_policy": "patient-disjoint fixed chb01-chb10 manifest; windows never split independently",
        "recording_count": evaluated_recordings,
        "window_count": len(labels),
        "positive_windows": int(sum(labels)),
        "exclusions": exclusions,
        "metrics": build_metrics_report(
            labels=labels,
            scores=scores,
            patient_ids=patient_ids,
            duration_hours=duration_hours,
            threshold=inference.threshold,
            seed=seed,
        ),
    }


def _safe_reason(exc: Exception) -> str:
    """Reduce one local evaluation error to a path-free aggregate reason."""

    if isinstance(exc, FileNotFoundError):
        return "recording file unavailable"
    if isinstance(exc, (OSError, IOError)):
        return "recording could not be read or written"
    if isinstance(exc, ValueError):
        return "recording is incompatible with the model contract or labels"
    return "recording failed during evaluation"


def write_report(report: dict[str, Any], output: Path) -> None:
    """Write a JSON evaluation report without private recording paths."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_plots(report: dict[str, Any], output: Path) -> None:
    """Write optional offline evaluation plots from an aggregate report.

    Parameters
    ----------
    report : dict
        JSON-compatible report returned by :func:`evaluate_dataset`.
    output : pathlib.Path
        PNG path for the four-panel confusion, ROC, precision-recall, and
        calibration summary.

    Raises
    ------
    RuntimeError
        Raised when the optional matplotlib dependency is unavailable.
    ValueError
        Raised when the report does not contain enough binary-label data for
        a meaningful plot.

    Privacy
    -------
    The plot uses aggregate metrics only and never receives recording paths,
    patient identifiers, or waveform samples.
    """

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to write evaluation plots.") from exc

    metrics = report.get("metrics", {})
    classification = metrics.get("classification", {})
    confusion = np.asarray(classification.get("confusion_matrix", []), dtype=np.int64)
    roc = metrics.get("roc", {})
    precision_recall = metrics.get("precision_recall", {})
    calibration = metrics.get("calibration", {})
    if confusion.shape != (2, 2) or not roc.get("fpr") or not precision_recall.get("recall"):
        raise ValueError("The report does not contain enough data for evaluation plots.")

    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    axes[0, 0].imshow(confusion, cmap="Blues")
    axes[0, 0].set_title("Confusion matrix")
    axes[0, 0].set_xlabel("Predicted")
    axes[0, 0].set_ylabel("Reference")
    axes[0, 0].set_xticks((0, 1), ("Normal", "Seizure"))
    axes[0, 0].set_yticks((0, 1), ("Normal", "Seizure"))
    for row in range(2):
        for column in range(2):
            axes[0, 0].text(column, row, str(confusion[row, column]), ha="center", va="center")

    axes[0, 1].plot(roc["fpr"], roc["tpr"], label=f"AUC: {metrics.get('roc_auc') or 'n/a'}")
    axes[0, 1].plot((0, 1), (0, 1), "--", color="0.6")
    axes[0, 1].set_title("ROC curve")
    axes[0, 1].set_xlabel("False-positive rate")
    axes[0, 1].set_ylabel("True-positive rate")
    axes[0, 1].legend(loc="lower right")

    axes[1, 0].plot(precision_recall["recall"], precision_recall["precision"])
    axes[1, 0].set_title("Precision-recall curve")
    axes[1, 0].set_xlabel("Recall")
    axes[1, 0].set_ylabel("Precision")
    axes[1, 0].set_xlim(0, 1)
    axes[1, 0].set_ylim(0, 1)

    reliability = calibration.get("reliability", [])
    means = [item["mean_score"] for item in reliability]
    observed = [item["empirical_rate"] for item in reliability]
    axes[1, 1].plot((0, 1), (0, 1), "--", color="0.6", label="Perfect calibration")
    axes[1, 1].plot(means, observed, "o-", label="Observed")
    axes[1, 1].set_title("Reliability diagram")
    axes[1, 1].set_xlabel("Mean model score")
    axes[1, 1].set_ylabel("Empirical seizure rate")
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].legend(loc="lower right")

    figure.suptitle(
        f"CHB-MIT evaluation · {report.get('privacy_method', 'unknown')} · {report.get('split', 'unknown')}"
    )
    figure.savefig(output, dpi=150)
    plt.close(figure)
