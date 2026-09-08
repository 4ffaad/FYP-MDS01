"""Non-clinical window-score summaries for stored model outputs."""

from __future__ import annotations

from backend.app.ml.interface import WindowPrediction


def build_score_summary(
    *,
    record_id: str,
    prediction: WindowPrediction,
    model_name: str,
    model_version: str,
    threshold: float = 0.5,
    calibration_version: str | None = None,
    calibration_dataset: str | None = None,
    privacy_method: str | None = None,
) -> dict:
    """Build an explicitly non-clinical summary of one model score.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    prediction : WindowPrediction
        Prediction metadata to include in the artifact.
    model_name : str
        Runtime model name stored with the prediction.
    model_version : str
        Runtime model version stored with the prediction.
    threshold : float
        Alert threshold used to classify this model window.

    Returns
    -------
    dict
        JSON-compatible artifact payload stored in database metadata.
    """

    development = prediction.score_type == "development_score"
    method = "development-stub" if development else "window-score-summary"
    return {
        "record_id": record_id,
        "window_index": prediction.window_index,
        "method": method,
        "model_name": model_name,
        "model_version": model_version,
        "is_clinical": False,
        "note": (
            "This is a deterministic development artifact, not a clinical explanation."
            if development
            else "This stores the model window score and threshold outcome; it is not a clinical explanation."
        ),
        "window_start_seconds": prediction.start_seconds,
        "window_end_seconds": prediction.end_seconds,
        "threshold": threshold,
        "probability": prediction.probability,
        "raw_score": prediction.raw_score,
        "calibrated_probability": prediction.calibrated_probability,
        "score_type": prediction.score_type,
        "calibration_method": prediction.calibration_method,
        "calibration_version": calibration_version or prediction.calibration_version,
        "calibration_dataset": calibration_dataset or prediction.calibration_dataset,
        "privacy_method": privacy_method,
    }
