"""Deterministic, explicitly non-clinical inference stub."""

from __future__ import annotations

import hashlib
import numpy as np

from backend.app.core.config import MODEL_NAME, MODEL_THRESHOLD, MODEL_VERSION
from backend.app.ml.interface import WindowPrediction


def _stable_probability(value: str) -> float:
    """Return a deterministic development-only value in the range [0, 1]."""

    raw = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)


class StubInferenceService:
    """Deterministic non-clinical adapter used until the real model arrives."""

    model_name = MODEL_NAME
    model_version = MODEL_VERSION
    threshold = MODEL_THRESHOLD

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
    ) -> list[WindowPrediction]:
        """Generate reproducible placeholder predictions for model windows.

        Parameters
        ----------
        windows : numpy.ndarray
            Float32 model input with shape ``(N, 1024, 18)``. Values are not
            used to make a clinical claim; shape validation is still enforced.
        window_starts : numpy.ndarray
            Start time in seconds for each window.
        record_id : str
            Opaque recording identifier used to make output reproducible.

        Returns
        -------
        list[WindowPrediction]
            One explicitly non-clinical prediction per window.

        Raises
        ------
        ValueError
            Raised when the model-input shape is incompatible with the
            configured contract.
        """

        if windows.ndim != 3 or windows.shape[1:] != (1024, 18):
            raise ValueError("Model input must have shape (N, 1024, 18).")
        predictions: list[WindowPrediction] = []
        for index, start in enumerate(window_starts.tolist()):
            window_digest = hashlib.sha256(windows[index].tobytes()).hexdigest()
            probability = _stable_probability(f"{record_id}:{index}:{window_digest}")
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
