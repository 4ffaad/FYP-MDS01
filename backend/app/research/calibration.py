"""Small, dependency-free temperature-scaling utilities for EEG scores."""

from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np


def _arrays(labels: Sequence[int], scores: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Validate binary labels and finite probabilities in the closed unit interval."""

    truth = np.asarray(labels, dtype=np.float64)
    values = np.asarray(scores, dtype=np.float64)
    if truth.ndim != 1 or values.ndim != 1 or len(truth) != len(values) or not len(truth):
        raise ValueError("Labels and scores must be non-empty one-dimensional arrays of equal length.")
    if not np.isin(truth, [0, 1]).all() or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("Labels must be binary and scores must be finite probabilities in [0, 1].")
    return truth, np.clip(values, 1e-6, 1 - 1e-6)


def temperature_scale(scores: Sequence[float], temperature: float) -> np.ndarray:
    """Apply temperature scaling to sigmoid probabilities through their logits."""

    if not isinstance(temperature, (int, float)) or not math.isfinite(float(temperature)) or temperature <= 0:
        raise ValueError("Temperature must be a finite positive number.")
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("Scores must be finite probabilities in [0, 1].")
    clipped = np.clip(values, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped))
    return 1.0 / (1.0 + np.exp(-logits / float(temperature)))


def negative_log_likelihood(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Return binary negative log-likelihood for probability calibration reports."""

    truth, values = _arrays(labels, probabilities)
    return float(-np.mean(truth * np.log(values) + (1.0 - truth) * np.log1p(-values)))


def fit_temperature(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Fit one positive temperature by held-out negative log-likelihood.

    The bounded scalar search deliberately uses NumPy and the standard library
    only. It is deterministic and sufficient for one-dimensional post-hoc
    calibration, without adding an optimizer dependency to the API runtime.
    """

    truth, values = _arrays(labels, scores)
    if len(np.unique(truth)) < 2:
        raise ValueError("Temperature scaling requires both negative and positive labels.")
    logits = np.log(values / (1.0 - values))

    def loss(log_temperature: float) -> float:
        scaled = logits / math.exp(log_temperature)
        return float(np.mean(np.logaddexp(0.0, scaled) - truth * scaled))

    grid = np.linspace(-5.0, 5.0, 161)
    losses = np.asarray([loss(value) for value in grid])
    best_index = int(np.argmin(losses))
    left = float(grid[max(0, best_index - 1)])
    right = float(grid[min(len(grid) - 1, best_index + 1)])
    if left == right:
        return float(math.exp(left))

    golden_ratio = (math.sqrt(5.0) - 1.0) / 2.0
    first = right - golden_ratio * (right - left)
    second = left + golden_ratio * (right - left)
    for _ in range(48):
        if loss(first) <= loss(second):
            right, second = second, first
            first = right - golden_ratio * (right - left)
        else:
            left, first = first, second
            second = left + golden_ratio * (right - left)
    return float(math.exp((left + right) / 2.0))
