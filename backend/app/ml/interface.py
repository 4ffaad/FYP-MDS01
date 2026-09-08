"""Stable interface between EEG preprocessing and model runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


def score_crossed_threshold(score: float, threshold: float) -> bool:
    """Return whether a model score meets the inclusive alert threshold.

    Parameters
    ----------
    score : float
        The exact score persisted for or returned by a model window.
    threshold : float
        The configured alert boundary.

    Returns
    -------
    bool
        ``True`` when ``score`` is greater than or equal to ``threshold``.
    """

    return float(score) >= float(threshold)


@dataclass(frozen=True)
class WindowPrediction:
    """Serializable model output for one fixed-duration EEG window."""

    window_index: int
    start_seconds: float
    end_seconds: float
    probability: float
    seizure_detected: bool
    score_type: str = "development_score"
    calibration_method: str | None = None
    raw_score: float | None = None
    calibrated_probability: float | None = None
    calibration_version: str | None = None
    calibration_dataset: str | None = None


class InferenceService(Protocol):
    """Structural interface implemented by real and development runtimes."""

    model_name: str
    model_version: str
    threshold: float
    score_type: str
    calibration_method: str | None

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
        privacy_method: str = "metadata-scrub",
    ) -> list[WindowPrediction]:
        """Return one prediction for each model-input window."""

        ...
