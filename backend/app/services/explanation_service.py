"""Explanation artifact generation with a non-clinical stub method."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.ml.interface import WindowPrediction


def write_stub_explanation(
    path: Path,
    *,
    record_id: str,
    prediction: WindowPrediction,
) -> dict:
    """Write a deterministic, explicitly non-clinical explanation artifact.

    Parameters
    ----------
    path : pathlib.Path
        Destination path inside the session explanation directory.
    record_id : str
        Opaque recording identifier.
    prediction : WindowPrediction
        Prediction metadata to include in the artifact.

    Returns
    -------
    dict
        JSON-compatible artifact payload written to disk.
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
