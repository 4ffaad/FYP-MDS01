"""Safe recording, prediction, explanation, and signal endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
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
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.model_input import MODEL_CHANNELS
from backend.app.core.config import BACKEND_ROOT, ENABLE_SIGNAL_PREVIEW


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
    return {
        "record_id": record.record_id,
        "model": (
            {
                "name": predictions[0].model_name,
                "version": predictions[0].model_version,
            }
            if predictions
            else None
        ),
        "predictions": [
            {
                "window_index": item.window_index,
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
                "probability": item.probability,
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
    """Return a bounded, downsampled view of de-identified EEG signal data.

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

    Returns
    -------
    dict
        Channel labels, sampling rate, timing metadata, and bounded samples.

    Raises
    ------
    fastapi.HTTPException
        Raised when the de-identified signal is unavailable or unreadable.
    """

    if not ENABLE_SIGNAL_PREVIEW:
        raise HTTPException(status_code=404, detail="Signal preview is disabled.")
    record = _get_record(db, record_id)
    if not record.deidentified_path:
        raise HTTPException(status_code=409, detail="De-identified signal is not available.")
    try:
        signal_path = Path(record.deidentified_path)
        if not signal_path.is_absolute():
            signal_path = BACKEND_ROOT / signal_path
        signals, sampling_rate, labels = read_uniform_edf(signal_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Signal could not be read.") from exc

    channel_indices = [labels.index(label) for label in MODEL_CHANNELS if label in labels]
    if len(channel_indices) == len(MODEL_CHANNELS):
        signals = signals[channel_indices]
        labels = list(MODEL_CHANNELS)

    start = min(int(start_seconds * sampling_rate), signals.shape[1])
    end = min(int((start_seconds + duration_seconds) * sampling_rate), signals.shape[1])
    selected = signals[:, start:end]
    actual_duration = (end - start) / sampling_rate
    if selected.shape[1] > max_points:
        indices = np.linspace(0, selected.shape[1] - 1, max_points, dtype=int)
        selected = selected[:, indices]
    return {
        "record_id": record.record_id,
        "sampling_rate": sampling_rate,
        "channel_labels": labels,
        "start_seconds": start / sampling_rate,
        "duration_seconds": actual_duration,
        "samples": selected.tolist(),
    }
