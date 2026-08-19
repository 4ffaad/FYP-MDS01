"""Explanation artifact generation with a non-clinical stub method."""

from __future__ import annotations

from backend.app.ml.interface import WindowPrediction


def build_stub_explanation(
    *,
    record_id: str,
    prediction: WindowPrediction,
) -> dict:
    """Build a deterministic, explicitly non-clinical explanation payload.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    prediction : WindowPrediction
        Prediction metadata to include in the artifact.

    Returns
    -------
    dict
        JSON-compatible artifact payload stored in database metadata.
    """

    payload = {
        "record_id": record_id,
        "window_index": prediction.window_index,
        "method": "development-stub",
        "is_clinical": False,
        "note": "This is a deterministic development artifact, not a clinical explanation.",
        "window_start_seconds": prediction.start_seconds,
        "window_end_seconds": prediction.end_seconds,
        "probability": prediction.probability,
    }
    return payload
