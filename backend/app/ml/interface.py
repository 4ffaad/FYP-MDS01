"""Stable interface between EEG preprocessing and model runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class WindowPrediction:
    window_index: int
    start_seconds: float
    end_seconds: float
    probability: float
    seizure_detected: bool


class InferenceService(Protocol):
    model_name: str
    model_version: str
    threshold: float

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
    ) -> list[WindowPrediction]: ...

