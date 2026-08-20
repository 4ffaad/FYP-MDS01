"""Safe recording, prediction, explanation, and signal endpoints."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from backend.app.database.db import get_session
from backend.app.database.models.eeg import EEGRecording
from backend.app.database.repository import (
    get_recording_by_public_id,
    get_session_by_database_id,
    list_flagged_window_counts,
    list_explanations,
    list_predictions,
)
from backend.app.services.session_service import public_record


router = APIRouter(prefix="/api", tags=["recordings"])


def _get_record(db: Session, record_id: str) -> EEGRecording:
    """Load a recording by its public identifier or raise HTTP 404.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session for the request.
    record_id : str
        Opaque recording identifier supplied by the client.

    Returns
    -------
    EEGRecording
        The matching recording row.

    Raises
    ------
    fastapi.HTTPException
        Raised with status 404 when the recording does not exist.
    """

    record = get_recording_by_public_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Recording was not found.")
    return record


@router.get("/recordings/{record_id}")
def get_recording(record_id: str, db: Session = Depends(get_session)) -> dict:
    """Return safe technical metadata for one recording.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Public recording metadata without patient references or filesystem
        paths.
    """

    record = _get_record(db, record_id)
    session = get_session_by_database_id(db, record.session_db_id)
    alert_count = list_flagged_window_counts(db, [record.id] if record.id is not None else []).get(record.id or 0, 0)
    return public_record(record, session, alert_count)


@router.get("/recordings/{record_id}/prediction")
def get_prediction(record_id: str, db: Session = Depends(get_session)) -> dict:
    """Return model metadata and window predictions for a recording.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Model version and one safe prediction object per EEG window.
    """

    record = _get_record(db, record_id)
    predictions = list_predictions(db, record.id)
    first = predictions[0] if predictions else None
    score_type = first.score_type if first else None
    calibrated = any(item.calibrated_probability is not None for item in predictions)
    return {
        "record_id": record.record_id,
        "model": (
            {
                "name": first.model_name,
                "version": first.model_version,
                "threshold": first.threshold,
                "score_type": score_type,
                "calibrated": calibrated,
                "calibration_method": first.calibration_method,
            }
            if first
            else None
        ),
        "summary": {
            "window_count": len(predictions),
            "flagged_window_count": sum(item.seizure_detected for item in predictions),
            "flagged_window_fraction": (
                sum(item.seizure_detected for item in predictions) / len(predictions)
                if predictions else 0.0
            ),
            "peak_window_score": max((item.probability for item in predictions), default=0.0),
            "aggregation_unit": "window",
            "recording_probability_available": calibrated,
        },
        "predictions": [
            {
                "window_index": item.window_index,
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
                "score": item.probability,
                "probability": item.probability,
                "raw_score": item.raw_score,
                "calibrated_probability": item.calibrated_probability,
                "score_type": item.score_type,
                "seizure_detected": item.seizure_detected,
            }
            for item in predictions
        ],
    }


@router.get("/recordings/{record_id}/explanation")
def get_explanation(record_id: str, db: Session = Depends(get_session)) -> dict:
    """Return stored non-clinical explanation artifacts for a recording.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Explanation metadata and JSON payloads when the artifact is readable.
        Internal artifact paths are never returned.
    """

    record = _get_record(db, record_id)
    predictions = list_predictions(db, record.id)
    prediction_ids = [prediction.id for prediction in predictions if prediction.id is not None]
    explanations = list_explanations(db, prediction_ids)
    items = []
    for explanation in explanations:
        payload = None
        if explanation.explanation_data:
            try:
                payload = json.loads(explanation.explanation_data)
            except json.JSONDecodeError:
                payload = None
        items.append({
            "method": explanation.method,
            "is_clinical": explanation.is_clinical,
            "data": payload,
        })
    return {"record_id": record.record_id, "explanations": items}


@router.get("/recordings/{record_id}/signal")
def get_signal(
    record_id: str,
    start_seconds: float = Query(0, ge=0),
    duration_seconds: float = Query(10, gt=0, le=60),
    max_points: int = Query(2000, gt=0, le=10000),
    db: Session = Depends(get_session),
) -> dict:
    """Reject waveform access because EEG remains biometrically sensitive.

    Parameters
    ----------
    record_id : str
        Opaque recording identifier.
    start_seconds : float
        Start time within the recording, defaulting to zero.
    duration_seconds : float
        Requested duration, limited to sixty seconds.
    max_points : int
        Maximum number of samples returned per channel.
    db : sqlmodel.Session
        Request-scoped database session.

    Raises
    ------
    fastapi.HTTPException
        Always raised with HTTP 404. Waveform data is not served by the
        privacy-first prototype.
    """
    raise HTTPException(status_code=404, detail="Waveform access is disabled for this privacy-first prototype.")
