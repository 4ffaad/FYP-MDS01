"""Offline seizure-utility and calibration metrics for labelled research data."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np


def _arrays(labels: Sequence[int], scores: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Validate and return binary labels and bounded scores as arrays."""

    truth = np.asarray(labels, dtype=np.int8)
    values = np.asarray(scores, dtype=np.float64)
    if truth.ndim != 1 or values.ndim != 1 or len(truth) != len(values) or not len(truth):
        raise ValueError("Labels and scores must be non-empty one-dimensional arrays of equal length.")
    if not np.isin(truth, [0, 1]).all() or not np.isfinite(values).all():
        raise ValueError("Labels must be binary and scores must be finite.")
    return truth, np.clip(values, 0.0, 1.0)


def classification_metrics(
    labels: Sequence[int],
    scores: Sequence[float],
    *,
    threshold: float = 0.5,
    duration_hours: float | None = None,
) -> dict[str, float | int | list[list[int]] | None]:
    """Return thresholded detection metrics for offline labelled recordings.

    Parameters
    ----------
    labels : sequence of int
        Ground-truth window labels, where 1 means seizure overlap meets the
        research rule.
    scores : sequence of float
        Model window scores in the range 0 to 1.
    threshold : float
        Decision threshold used to create alerts.
    duration_hours : float or None
        Labelled recording duration used for false alarms per hour.

    Returns
    -------
    dict
        Confusion matrix, accuracy, sensitivity, specificity, precision,
        recall, F1, and false alarms per hour.
    """

    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1.")
    truth, values = _arrays(labels, scores)
    predicted = values >= threshold
    tn = int(np.sum((truth == 0) & ~predicted))
    fp = int(np.sum((truth == 0) & predicted))
    fn = int(np.sum((truth == 1) & ~predicted))
    tp = int(np.sum((truth == 1) & predicted))
    positive = tp + fn
    negative = tn + fp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / positive if positive else 0.0
    specificity = tn / negative if negative else 0.0
    accuracy = (tp + tn) / len(truth)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_alarms_per_hour = None if duration_hours is None or duration_hours <= 0 else fp / duration_hours
    return {
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "accuracy": accuracy,
        "sensitivity": recall,
        "specificity": specificity,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_alarms_per_hour": false_alarms_per_hour,
        "threshold": threshold,
        "support": len(truth),
    }


def roc_points(labels: Sequence[int], scores: Sequence[float]) -> dict[str, list[float]]:
    """Return ROC false-positive and true-positive points without a dependency."""

    truth, values = _arrays(labels, scores)
    thresholds = np.r_[np.inf, np.sort(np.unique(values))[::-1], -np.inf]
    positives = max(1, int(np.sum(truth == 1)))
    negatives = max(1, int(np.sum(truth == 0)))
    fpr: list[float] = []
    tpr: list[float] = []
    for threshold in thresholds:
        predicted = values >= threshold
        fpr.append(float(np.sum((truth == 0) & predicted) / negatives))
        tpr.append(float(np.sum((truth == 1) & predicted) / positives))
    return {"fpr": fpr, "tpr": tpr, "thresholds": [float(item) for item in thresholds]}


def precision_recall_points(labels: Sequence[int], scores: Sequence[float]) -> dict[str, list[float]]:
    """Return precision-recall points for threshold analysis."""

    truth, values = _arrays(labels, scores)
    thresholds = np.r_[np.sort(np.unique(values))[::-1], -np.inf]
    precision: list[float] = []
    recall: list[float] = []
    for threshold in thresholds:
        predicted = values >= threshold
        tp = int(np.sum((truth == 1) & predicted))
        fp = int(np.sum((truth == 0) & predicted))
        fn = int(np.sum((truth == 1) & ~predicted))
        precision.append(tp / (tp + fp) if tp + fp else 1.0)
        recall.append(tp / (tp + fn) if tp + fn else 0.0)
    return {"precision": precision, "recall": recall, "thresholds": [float(item) for item in thresholds]}


def calibration_metrics(
    labels: Sequence[int],
    probabilities: Sequence[float],
    *,
    bins: int = 10,
) -> dict[str, float | list[dict[str, float | int]]]:
    """Return reliability bins, Brier score, and expected calibration error."""

    if bins < 2:
        raise ValueError("Calibration requires at least two bins.")
    truth, values = _arrays(labels, probabilities)
    edges = np.linspace(0.0, 1.0, bins + 1)
    reliability: list[dict[str, float | int]] = []
    weighted_error = 0.0
    for index in range(bins):
        included = (values >= edges[index]) & (values <= edges[index + 1] if index == bins - 1 else values < edges[index + 1])
        count = int(np.sum(included))
        if not count:
            continue
        observed = float(np.mean(truth[included]))
        predicted = float(np.mean(values[included]))
        weighted_error += count / len(truth) * abs(observed - predicted)
        reliability.append({"count": count, "mean_score": predicted, "empirical_rate": observed})
    return {
        "brier_score": float(np.mean((values - truth) ** 2)),
        "expected_calibration_error": float(weighted_error),
        "reliability": reliability,
    }


def threshold_sweep(labels: Sequence[int], scores: Sequence[float], thresholds: Iterable[float]) -> list[dict[str, float | int | list[list[int]] | None]]:
    """Return classification metrics for each explicitly selected threshold."""

    return [classification_metrics(labels, scores, threshold=threshold) for threshold in thresholds]


def patient_bootstrap_f1(
    labels: Sequence[int],
    scores: Sequence[float],
    patient_ids: Sequence[str],
    *,
    threshold: float = 0.5,
    repeats: int = 1000,
    seed: int = 0,
) -> dict[str, float]:
    """Estimate patient-level F1 confidence bounds without window resampling.

    Windows from one patient are sampled together, preventing correlated
    windows from pretending to be independent patients.
    """

    truth, values = _arrays(labels, scores)
    groups = np.asarray(patient_ids, dtype=object)
    if groups.ndim != 1 or len(groups) != len(truth):
        raise ValueError("patient_ids must contain one value per window.")
    unique = np.unique(groups)
    if len(unique) < 2:
        raise ValueError("At least two patients are required for patient bootstrap.")
    rng = np.random.default_rng(seed)
    results: list[float] = []
    for _ in range(repeats):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        indexes = np.concatenate([np.flatnonzero(groups == patient) for patient in sampled])
        results.append(float(classification_metrics(truth[indexes], values[indexes], threshold=threshold)["f1"]))
    lower, upper = np.percentile(results, [2.5, 97.5])
    return {"f1": float(classification_metrics(truth, values, threshold=threshold)["f1"]), "lower_95": float(lower), "upper_95": float(upper), "seed": float(seed)}
