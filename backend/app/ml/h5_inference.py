"""Fail-closed adapter for a manually reviewed Keras H5 seizure model."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from backend.app.ml.interface import WindowPrediction


class H5ModelError(RuntimeError):
    """Raised when a real H5 model has not passed its review gate."""


class H5InferenceService:
    """Run a reviewed binary Keras model on the fixed private EEG contract."""

    def __init__(self, model_path: Path, contract_path: Path) -> None:
        """Load a reviewed model contract and validate the model's input/output shapes."""

        try:
            import tensorflow as tf
        except ImportError as exc:
            raise H5ModelError("TensorFlow is required for MODEL_RUNTIME=h5.") from exc
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise H5ModelError("A reviewed H5 model contract is required.") from exc
        if not contract.get("reviewed"):
            raise H5ModelError("The H5 model contract has not been manually reviewed.")
        if contract.get("input_shape") != [1024, 18]:
            raise H5ModelError("The reviewed H5 model contract is not compatible with (N, 1024, 18).")
        if contract.get("output_semantics") != "seizure-probability":
            raise H5ModelError("The reviewed H5 model output must be seizure-probability.")
        if not isinstance(contract.get("training_preprocessing"), str) or not contract["training_preprocessing"].strip():
            raise H5ModelError("The reviewed H5 model must document its training-time preprocessing.")
        threshold = contract.get("threshold")
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise H5ModelError("The reviewed H5 model requires a probability threshold in [0, 1].")
        self.model = tf.keras.models.load_model(model_path, compile=False)
        input_shape = tuple(self.model.input_shape)
        output_shape = tuple(self.model.output_shape)
        if input_shape[1:] != (1024, 18) or output_shape[1:] != (1,):
            raise H5ModelError("The H5 model shape differs from its reviewed contract.")
        self.model_name = str(contract.get("model_name", model_path.stem))
        self.model_version = str(contract.get("model_version", "reviewed-h5"))
        self.threshold = float(threshold)
        self.score_type = str(contract.get("score_type", "uncalibrated_probability"))
        self.calibration_method = contract.get("calibration_method")
        self.temperature = contract.get("temperature")
        if self.score_type not in {"uncalibrated_probability", "calibrated_probability"}:
            raise H5ModelError("The reviewed H5 model score_type is not supported.")
        if self.score_type == "calibrated_probability" and not self.calibration_method:
            raise H5ModelError("A calibrated H5 model must document its calibration method.")
        if self.score_type == "calibrated_probability" and self.calibration_method != "temperature_scaling":
            raise H5ModelError("Only reviewed temperature_scaling calibration is supported.")
        if self.score_type == "calibrated_probability" and self.calibration_method == "temperature_scaling":
            if not isinstance(self.temperature, (int, float)) or self.temperature <= 0:
                raise H5ModelError("Temperature scaling requires a positive reviewed temperature.")

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
    ) -> list[WindowPrediction]:
        """Return thresholded seizure probabilities for private model windows."""

        if windows.ndim != 3 or windows.shape[1:] != (1024, 18):
            raise ValueError("Model input must have shape (N, 1024, 18).")
        probabilities = np.asarray(self.model.predict(windows, verbose=0)).reshape(-1)
        if len(probabilities) != len(window_starts) or np.any((probabilities < 0) | (probabilities > 1)):
            raise H5ModelError("The H5 model did not return one probability per input window.")
        predictions: list[WindowPrediction] = []
        for index, (start, raw_score) in enumerate(zip(window_starts, probabilities)):
            calibrated_probability = None
            score = float(raw_score)
            if self.score_type == "calibrated_probability" and self.calibration_method == "temperature_scaling":
                clipped = min(max(score, 1e-6), 1 - 1e-6)
                logit = math.log(clipped / (1 - clipped))
                calibrated_probability = 1 / (1 + math.exp(-logit / float(self.temperature)))
                score = calibrated_probability
            predictions.append(
                WindowPrediction(
                    window_index=index,
                    start_seconds=float(start),
                    end_seconds=float(start + 4),
                    probability=score,
                    seizure_detected=bool(score >= self.threshold),
                    score_type=self.score_type,
                    calibration_method=self.calibration_method,
                    raw_score=float(raw_score),
                    calibrated_probability=calibrated_probability,
                )
            )
        return predictions
