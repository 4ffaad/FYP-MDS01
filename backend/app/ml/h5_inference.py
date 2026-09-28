"""Fail-closed adapter for a manually reviewed Keras H5 seizure model."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from backend.app.core.config import H5_CONTRACT_SHA256
from backend.app.eeg.model_input import (
    MODEL_CHANNELS,
    MODEL_SAMPLING_RATE,
    WINDOW_SECONDS,
    WINDOW_STEP_SECONDS,
    validate_model_windows,
)
from backend.app.ml.h5_compat import h5_custom_objects
from backend.app.ml.interface import WindowPrediction, score_crossed_threshold
from backend.app.privacy.methods import CANONICAL_BASELINE, CANONICAL_COMBINED, canonical_privacy_profile


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
        if len(H5_CONTRACT_SHA256) != 64 or _sha256_file(contract_path) != H5_CONTRACT_SHA256:
            raise H5ModelError("The H5 model contract does not match its independent hash.")
        if not contract.get("reviewed"):
            raise H5ModelError("The H5 model contract has not been manually reviewed.")
        if contract.get("input_shape") != [1024, 18]:
            raise H5ModelError("The reviewed H5 model contract is not compatible with (N, 1024, 18).")
        if contract.get("input_dtype") != "float32":
            raise H5ModelError("The reviewed H5 model must accept float32 inputs.")
        if contract.get("channel_order") != list(MODEL_CHANNELS):
            raise H5ModelError("The reviewed H5 model channel order differs from the EDF contract.")
        sampling_rate = contract.get("sampling_rate")
        if type(sampling_rate) is not int or sampling_rate != MODEL_SAMPLING_RATE:
            raise H5ModelError("The reviewed H5 model sampling rate differs from the EDF contract.")
        window_seconds = contract.get("window_seconds")
        if type(window_seconds) is not int or window_seconds != WINDOW_SECONDS:
            raise H5ModelError("The reviewed H5 model window length differs from the EDF contract.")
        window_stride_seconds = contract.get("window_stride_seconds")
        if (
            isinstance(window_stride_seconds, bool)
            or not isinstance(window_stride_seconds, (int, float))
            or window_stride_seconds != WINDOW_STEP_SECONDS
        ):
            raise H5ModelError("The reviewed H5 model window stride differs from the training contract.")
        if contract.get("output_semantics") != "seizure-probability":
            raise H5ModelError("The reviewed H5 model output must be seizure-probability.")
        if contract.get("output_shape") != [1]:
            raise H5ModelError("The reviewed H5 output shape must be one score per input window.")
        expected_output_dtype = contract.get("output_dtype")
        if expected_output_dtype not in {"float32", "float64"}:
            raise H5ModelError("The reviewed H5 output dtype is missing or unsupported.")
        expected_activation = contract.get("last_layer_activation")
        if not isinstance(expected_activation, str) or not expected_activation.strip():
            raise H5ModelError("The reviewed H5 output activation is missing.")
        expected_sha256 = contract.get("artifact_sha256")
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
            raise H5ModelError("The reviewed H5 model contract must include its artifact SHA-256.")
        if _sha256_file(model_path) != expected_sha256:
            raise H5ModelError("The H5 artifact does not match the reviewed contract hash.")
        if not isinstance(contract.get("training_preprocessing"), str) or not contract["training_preprocessing"].strip():
            raise H5ModelError("The reviewed H5 model must document its training-time preprocessing.")
        threshold = contract.get("threshold")
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise H5ModelError("The reviewed H5 model requires a score threshold in [0, 1].")
        self.model = tf.keras.models.load_model(
            model_path,
            compile=False,
            custom_objects=h5_custom_objects(tf),
        )
        input_shape = tuple(self.model.input_shape)
        output_shape = tuple(self.model.output_shape)
        input_dtype = str(getattr(self.model.inputs[0], "dtype", "unknown"))
        output_dtype = str(getattr(self.model.outputs[0], "dtype", "unknown"))
        if (
            input_shape != (None, 1024, 18)
            or output_shape != (None, 1)
            or input_dtype != "float32"
        ):
            raise H5ModelError("The H5 model shape differs from its reviewed contract.")
        if output_dtype not in {"float32", "float64"}:
            raise H5ModelError("The H5 model output dtype is not supported.")
        if output_shape[1:] != tuple(contract["output_shape"]) or output_dtype != expected_output_dtype:
            raise H5ModelError("The loaded H5 output differs from the reviewed shape or dtype.")
        output_layer_activation = getattr(
            getattr(self.model.layers[-1], "activation", None), "__name__", None
        )
        if output_layer_activation != expected_activation:
            raise H5ModelError("The loaded H5 output activation differs from the reviewed contract.")
        self.model_name = str(contract.get("model_name", model_path.stem))
        self.model_version = str(contract.get("model_version", "reviewed-h5"))
        self.threshold = float(threshold)
        self.score_type = str(contract.get("score_type", "uncalibrated_probability"))
        self.calibration_method = contract.get("calibration_method")
        self.temperature = contract.get("temperature")
        self.calibration_profiles = contract.get("calibration_profiles", {})
        self.calibration_version = contract.get("calibration_version")
        self.calibration_dataset = contract.get("calibration_dataset")
        if self.score_type not in {"uncalibrated_probability", "calibrated_probability"}:
            raise H5ModelError("The reviewed H5 model score_type is not supported.")
        if self.score_type == "calibrated_probability":
            self._validate_calibration_profiles()

    def predict(
        self,
        windows: np.ndarray,
        window_starts: np.ndarray,
        record_id: str,
        privacy_method: str = CANONICAL_BASELINE,
    ) -> list[WindowPrediction]:
        """Return thresholded model scores for private model windows."""

        validate_model_windows(windows, window_starts)
        scores = np.asarray(self.model.predict(windows, verbose=0)).reshape(-1)
        if (
            len(scores) != len(window_starts)
            or not np.isfinite(scores).all()
            or np.any((scores < 0) | (scores > 1))
        ):
            raise H5ModelError("The H5 model did not return one score in its reviewed output range per window.")
        profile = self._calibration_profile(privacy_method)
        predictions: list[WindowPrediction] = []
        for index, (start, raw_score) in enumerate(zip(window_starts, scores)):
            calibrated_probability = None
            score = float(raw_score)
            calibration_method = None
            calibration_version = None
            calibration_dataset = None
            if self.score_type == "calibrated_probability":
                calibration_method = str(profile["method"])
                calibration_version = str(profile["version"])
                calibration_dataset = str(profile["dataset"])
                clipped = min(max(score, 1e-6), 1 - 1e-6)
                logit = math.log(clipped / (1 - clipped))
                calibrated_probability = 1 / (1 + math.exp(-logit / float(profile["temperature"])))
                score = calibrated_probability
            predictions.append(
                WindowPrediction(
                    window_index=index,
                    start_seconds=float(start),
                    end_seconds=float(start + 4),
                    probability=score,
                    seizure_detected=score_crossed_threshold(score, self.threshold),
                    score_type=self.score_type,
                    calibration_method=calibration_method,
                    raw_score=float(raw_score),
                    calibrated_probability=calibrated_probability,
                    calibration_version=calibration_version,
                    calibration_dataset=calibration_dataset,
                )
            )
        return predictions

    def _validate_calibration_profiles(self) -> None:
        """Require a complete reviewed calibration profile for each input privacy representation."""

        if self.calibration_method != "temperature_scaling":
            raise H5ModelError("Only reviewed temperature_scaling calibration is supported.")
        if not isinstance(self.calibration_profiles, dict):
            raise H5ModelError("A calibrated H5 model requires profile-specific calibration metadata.")
        for profile_name in (CANONICAL_BASELINE, CANONICAL_COMBINED):
            profile = self.calibration_profiles.get(profile_name)
            if not isinstance(profile, dict):
                raise H5ModelError(f"Calibration metadata is missing for {profile_name}.")
            if profile.get("status") != "active":
                raise H5ModelError(f"Calibration metadata is not active for {profile_name}.")
            if profile.get("method") != "temperature_scaling":
                raise H5ModelError(f"Calibration method is invalid for {profile_name}.")
            temperature = profile.get("temperature")
            if not isinstance(temperature, (int, float)) or not math.isfinite(float(temperature)) or temperature <= 0:
                raise H5ModelError(f"Calibration temperature is invalid for {profile_name}.")
            if not isinstance(profile.get("version"), str) or not profile["version"].strip():
                raise H5ModelError(f"Calibration version is missing for {profile_name}.")
            if not isinstance(profile.get("dataset"), str) or not profile["dataset"].strip():
                raise H5ModelError(f"Calibration dataset is missing for {profile_name}.")
            subjects = profile.get("subjects")
            if not isinstance(subjects, list) or not subjects or not all(isinstance(item, str) for item in subjects):
                raise H5ModelError(f"Calibration subjects are missing for {profile_name}.")
            metrics = profile.get("metrics")
            if not isinstance(metrics, dict) or not all(isinstance(metrics.get(key), (int, float)) for key in ("brier_score", "expected_calibration_error", "negative_log_likelihood")):
                raise H5ModelError(f"Calibration metrics are missing for {profile_name}.")

    def _calibration_profile(self, privacy_method: str) -> dict:
        """Return the calibrated profile for a canonical privacy selection."""

        try:
            canonical = canonical_privacy_profile(privacy_method)
        except ValueError as exc:
            raise H5ModelError("The active privacy profile is not supported for calibration.") from exc
        if self.score_type != "calibrated_probability":
            return {}
        profile = self.calibration_profiles.get(canonical)
        if not isinstance(profile, dict):
            raise H5ModelError(f"Calibration metadata is missing for {canonical}.")
        return profile


def _sha256_file(path: Path) -> str:
    """Return a file digest so a reviewed H5 contract cannot authorize a replacement artifact."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise H5ModelError("The reviewed H5 artifact is not readable.") from exc
    return digest.hexdigest()
