"""Session creation, safe serialization, and upload orchestration."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session

from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.repositories.recording_repository import list_for_session
from backend.app.database.repositories.session_repository import get_by_public_id, list_sessions
from backend.app.services.storage_service import SessionStorage


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
    patient_reference: str,
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
    patient_reference : str
        Restricted internal reference. It is stored in the database only.

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
        patient_reference=patient_reference.strip(),
        original_filename=Path(archive.filename or "upload.zip").name,
        original_path="",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    original_path = await storage.save_upload(session.session_id, archive)
    session.original_path = str(original_path)
    db.add(session)
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

    return get_by_public_id(db, session_id)


def public_record(record: EEGRecording) -> dict:
    """Serialize recording metadata without sensitive names or paths.

    Parameters
    ----------
    record : EEGRecording
        Internal recording row.

    Returns
    -------
    dict
        Safe API representation using generated display names.
    """

    return {
        "record_id": record.record_id,
        "sequence_index": record.sequence_index,
        "status": record.status.value,
        # Client filenames may contain patient identifiers. Expose only a
        # generated display name, never the submitted filename.
        "source_filename": f"recording_{record.sequence_index:02d}.edf",
        "duration_seconds": record.duration_seconds,
        "sampling_rate": record.sampling_rate,
        "channel_count": record.channel_count,
        "error_message": record.error_message,
    }


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

    records = list_for_session(db, session.id) if session.id is not None else []
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "current_stage": session.current_stage,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "error_message": session.error_message,
        "recordings": [public_record(record) for record in records],
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
