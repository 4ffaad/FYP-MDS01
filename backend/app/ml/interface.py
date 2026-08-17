"""Stable interface between EEG preprocessing and model runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class WindowPrediction:
    """Serializable model output for one fixed-duration EEG window."""

    window_index: int
    start_seconds: float
    end_seconds: float
    probability: float
    seizure_detected: bool


class InferenceService(Protocol):
    """Structural interface implemented by real and development runtimes."""

    model_name: str
    model_version: str
    threshold: float

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
    ) -> list[WindowPrediction]:
        """Return one prediction for each model-input window."""

        ...
