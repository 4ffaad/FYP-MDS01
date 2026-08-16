"""Deterministic, explicitly non-clinical inference stub."""

from __future__ import annotations

import numpy as np

from backend.app.core.config import MODEL_NAME, MODEL_THRESHOLD, MODEL_VERSION
from backend.app.ml.interface import WindowPrediction
from backend.app.privacy.hashing import stable_probability


class StubInferenceService:
    model_name = MODEL_NAME
    model_version = MODEL_VERSION
    threshold = MODEL_THRESHOLD

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
    ) -> list[WindowPrediction]:
        if windows.ndim != 3 or windows.shape[1:] != (1024, 18):
            raise ValueError("Model input must have shape (N, 1024, 18).")
        predictions: list[WindowPrediction] = []
        for index, start in enumerate(window_starts.tolist()):
            probability = stable_probability(f"{record_id}:{index}")
            predictions.append(
                WindowPrediction(
                    window_index=index,
                    start_seconds=float(start),
                    end_seconds=float(start + 4),
                    probability=probability,
                    seizure_detected=probability >= self.threshold,
                )
            )
        return predictions

