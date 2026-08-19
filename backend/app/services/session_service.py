"""Session creation, safe serialization, and upload orchestration."""

from __future__ import annotations

import json
import uuid

from fastapi import UploadFile
from sqlmodel import Session

from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.repository import (
    delete_session_data,
    get_session_by_public_id,
    list_flagged_window_counts,
    list_recordings_for_session,
    list_sessions,
)
from backend.app.services.storage_service import SessionStorage
from backend.app.database.models.eeg import AnalysisStatus


def new_session_id() -> str:
    """Generate an opaque public identifier for one uploaded session.

    Returns
    -------
    str
        Uppercase ``SES-`` identifier containing no patient data.
    """

    return f"SES-{uuid.uuid4().hex[:8].upper()}"


async def create_session(
    db: Session,
    storage: SessionStorage,
    archive: UploadFile,
    privacy_method: str = "control",
) -> EEGSession:
    """Persist an upload session and stream its ZIP into private storage.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used to create the session row.
    storage : SessionStorage
        Session-scoped storage implementation.
    archive : fastapi.UploadFile
        Client ZIP upload.
    privacy_method : str
        Selected research privacy mode stored with the session.

    Returns
    -------
    EEGSession
        Newly created session row with its private archive path.

    Raises
    ------
    StorageError
        Propagated when the upload exceeds limits or cannot be stored.
    """

    session = EEGSession(
        session_id=new_session_id(),
        privacy_method=privacy_method.strip(),
        original_filename="",
        original_path="",
    )
    db.add(session)
    db.flush()
    try:
        original_path = await storage.save_upload(session.session_id, archive)
    except Exception:
        storage.cleanup_session(session.session_id)
        db.rollback()
        raise
    session.original_path = str(original_path)
    db.commit()
    db.refresh(session)
    return session


def get_session_or_none(db: Session, session_id: str) -> EEGSession | None:
    """Look up a session by public ID without exposing internal identifiers.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    session_id : str
        Opaque public session identifier.

    Returns
    -------
    EEGSession or None
        Matching session row, if present.
    """

    return get_session_by_public_id(db, session_id)


def public_record(record: EEGRecording, session: EEGSession | None = None, model_alert_window_count: int = 0) -> dict:
    """Serialize recording metadata without sensitive names or paths.

    Parameters
    ----------
    record : EEGRecording
        Internal recording row.
    session : EEGSession or None
        Optional owning session used only when a direct recording response
        needs safe session context.
    model_alert_window_count : int
        Number of windows flagged by the model, without exposing prediction
        internals in the recording list response.

    Returns
    -------
    dict
        Safe API representation using generated display names.
    """

    reference_annotation = None
    if record.reference_annotation_source and record.reference_intervals_json is not None:
        try:
            intervals = json.loads(record.reference_intervals_json)
        except json.JSONDecodeError:
            intervals = []
        reference_annotation = {
            "source": record.reference_annotation_source,
            "intervals": [
                {"start_seconds": float(start), "end_seconds": float(end)}
                for start, end in intervals
                if float(end) > float(start) >= 0
            ],
        }

    payload = {
        "record_id": record.record_id,
        "sequence_index": record.sequence_index,
        "status": record.status.value,
        # Client filenames may contain patient identifiers. Expose only a
        # generated display name, never the submitted filename.
        "source_filename": f"recording_{record.sequence_index:02d}.edf",
        "duration_seconds": record.duration_seconds,
        "sampling_rate": record.sampling_rate,
        "channel_count": record.channel_count,
        "reference_annotation": reference_annotation,
        "model_alert_window_count": model_alert_window_count,
        "error_message": record.error_message,
    }
    if session is not None:
        payload.update({
            "session_id": session.session_id,
            "session_created_at": session.created_at.isoformat(),
            "privacy_method": session.privacy_method,
        })
    return payload


def public_session(db: Session, session: EEGSession) -> dict:
    """Serialize a session and its recordings for public API responses.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used to load recordings.
    session : EEGSession
        Internal session row.

    Returns
    -------
    dict
        Safe session status, timestamps, and recording summaries.
    """

    records = list_recordings_for_session(db, session.id) if session.id is not None else []
    alert_counts = list_flagged_window_counts(db, [record.id for record in records if record.id is not None])
    completed_count = sum(record.status.value == "inferred" for record in records)
    failed_count = sum(record.status.value == "failed" for record in records)
    finished_count = completed_count + failed_count
    annotated_count = sum(
        bool(record.reference_intervals_json and json.loads(record.reference_intervals_json))
        for record in records
        if record.reference_intervals_json
    )
    labelled_count = sum(record.reference_annotation_source is not None for record in records)
    public_records = []
    for record in records:
        payload = public_record(record, model_alert_window_count=alert_counts.get(record.id or 0, 0))
        public_records.append(payload)
    return {
        "session_id": session.session_id,
        "privacy_method": session.privacy_method,
        "status": session.status.value,
        "current_stage": session.current_stage,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "error_message": session.error_message,
        "progress": {
            "total_recordings": len(records),
            "finished_recordings": finished_count,
            "completed_recordings": completed_count,
            "failed_recordings": failed_count,
            "percent": round((finished_count / len(records)) * 100) if records else 0,
        },
        "summary": {
            "dataset_seizure_recordings": annotated_count if labelled_count else None,
            "model_alert_recordings": sum(count > 0 for count in alert_counts.values()),
        },
        "recordings": public_records,
    }


def public_session_list(db: Session) -> list[dict]:
    """Serialize all sessions in newest-first order.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used to load rows.

    Returns
    -------
    list[dict]
        Safe public session summaries.
    """

    return [public_session(db, session) for session in list_sessions(db)]


def delete_session(db: Session, storage: SessionStorage, session: EEGSession) -> None:
    """Delete a completed session from storage and PostgreSQL.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for dependent-row deletion.
    storage : SessionStorage
        Private storage service used to remove the session directory.
    session : EEGSession
        Session being removed.

    Raises
    ------
    ValueError
        Raised when processing is still active to prevent a background task
        from writing new rows after deletion begins.
    """

    active = {
        AnalysisStatus.QUEUED,
        AnalysisStatus.VALIDATING,
        AnalysisStatus.DEIDENTIFYING,
        AnalysisStatus.PREPROCESSING,
        AnalysisStatus.INFERENCE,
        AnalysisStatus.EXPLAINING,
    }
    if session.status in active:
        raise ValueError("Wait until processing finishes before deleting this session.")
    storage.delete_session(session.session_id)
    delete_session_data(db, session)
