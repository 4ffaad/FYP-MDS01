"""Session creation, safe serialization, and upload orchestration."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from collections.abc import Iterable

from fastapi import UploadFile
from sqlmodel import Session

from backend.app.database.models.eeg import EEGRecording, EEGSession, UploadDraft, utc_now
from backend.app.database.repository import (
    delete_session_data,
    get_session_by_public_id,
    list_flagged_prediction_windows,
    list_flagged_window_counts,
    list_model_metadata,
    list_recordings_for_session,
    list_recordings_for_sessions,
    list_sessions,
    get_upload_draft,
    list_expired_upload_drafts,
)
from backend.app.services.storage_service import SessionStorage
from backend.app.services.case_service import new_case_id
from backend.app.database.models.eeg import AnalysisStatus
from backend.app.privacy.methods import (
    canonical_privacy_profile,
    methods_from_profile,
)
from backend.app.privacy.retention import model_alert_intervals


def new_session_id() -> str:
    """Generate an opaque public identifier for one uploaded session.

    Returns
    -------
    str
        Uppercase ``SES-`` identifier containing no patient data.
    """

    return f"SES-{secrets.token_hex(16).upper()}"


def new_draft_id() -> str:
    """Generate an opaque identifier for one staged upload."""

    return f"UPL-{secrets.token_hex(16).upper()}"


def _is_expired(expires_at: datetime) -> bool:
    """Compare a database expiry timestamp safely across SQLite and PostgreSQL."""

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= utc_now()


def cleanup_expired_drafts(db: Session, storage: SessionStorage) -> None:
    """Remove expired draft rows and their encrypted private files."""

    expired = list_expired_upload_drafts(db, utc_now())
    if not expired:
        return
    storage.cleanup_expired_drafts([draft.draft_id for draft in expired])
    for draft in expired:
        db.delete(draft)
    db.commit()


async def create_upload_draft(
    db: Session,
    storage: SessionStorage,
    archive: UploadFile,
    expires_at: datetime,
    owner_user_id: int | None = None,
) -> UploadDraft:
    """Encrypt and persist a ZIP while waiting for privacy configuration.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used to persist the draft metadata.
    storage : SessionStorage
        Private storage service used for AES-GCM encryption.
    archive : fastapi.UploadFile
        ZIP archive supplied by the client.
    expires_at : datetime
        UTC expiry timestamp for the staged upload.

    Returns
    -------
    UploadDraft
        Persisted draft containing only opaque metadata.

    Raises
    ------
    Exception
        Storage or database errors are rolled back and propagated.
    """

    draft_id = new_draft_id()
    draft = UploadDraft(
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        encrypted_path="",
        expires_at=expires_at,
    )
    db.add(draft)
    db.flush()
    try:
        encrypted_path = await storage.save_draft_upload(draft_id, archive)
        draft.encrypted_path = str(encrypted_path)
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return draft
    except Exception:
        db.rollback()
        storage.delete_draft(draft_id)
        raise


def finalize_upload_draft(
    db: Session,
    storage: SessionStorage,
    draft_id: str,
    privacy_method: str = "metadata-scrub",
    privacy_methods: Iterable[str] | None = None,
    owner_user_id: int | None = None,
    case_id: str | None = None,
) -> EEGSession:
    """Convert one encrypted draft into a queued analysis session.

    The staged archive is copied without decrypting it, so a failed database
    commit leaves the encrypted draft available for a safe retry.
    """

    draft = get_upload_draft(db, draft_id, owner_user_id)
    if draft is None:
        raise ValueError("Upload draft was not found or has expired.")
    if _is_expired(draft.expires_at):
        storage.delete_draft(draft.draft_id)
        db.delete(draft)
        db.commit()
        raise ValueError("Upload draft has expired. Choose the archive again.")

    profile = canonical_privacy_profile(privacy_methods if privacy_methods is not None else privacy_method)
    session = EEGSession(
        owner_user_id=owner_user_id,
        session_id=new_session_id(),
        case_id=case_id or new_case_id(),
        privacy_method=profile,
        original_filename="",
        original_path="",
    )
    db.add(session)
    db.flush()
    try:
        original_path = storage.promote_draft(draft.draft_id, session.session_id)
        session.original_path = str(original_path)
        db.delete(draft)
        db.add(session)
        db.commit()
        db.refresh(session)
        storage.delete_draft(draft.draft_id)
        return session
    except Exception:
        db.rollback()
        storage.delete_session(session.session_id)
        raise


async def create_session(
    db: Session,
    storage: SessionStorage,
    archive: UploadFile,
    privacy_method: str = "metadata-scrub",
    privacy_methods: Iterable[str] | None = None,
    owner_user_id: int | None = None,
    case_id: str | None = None,
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

    profile = canonical_privacy_profile(privacy_methods if privacy_methods is not None else privacy_method)
    session = EEGSession(
        owner_user_id=owner_user_id,
        session_id=new_session_id(),
        case_id=case_id or new_case_id(),
        privacy_method=profile,
        original_filename="",
        original_path="",
    )
    db.add(session)
    db.flush()
    try:
        original_path = await storage.save_upload(session.session_id, archive)
        session.original_path = str(original_path)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    except Exception:
        db.rollback()
        storage.cleanup_session(session.session_id)
        raise


def get_session_or_none(db: Session, session_id: str, owner_user_id: int | None = None) -> EEGSession | None:
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

    return get_session_by_public_id(db, session_id, owner_user_id)


def public_record(
    record: EEGRecording,
    session: EEGSession | None = None,
    model_alert_window_count: int = 0,
    model_metadata: dict[str, str] | None = None,
    alert_intervals: list[tuple[float, float]] | None = None,
) -> dict:
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
    model_metadata : dict[str, str] or None
        Safe model name, version, and score semantics for completed recordings.

    Returns
    -------
    dict
        Safe API representation using generated display names.
    """

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
        "model_alert_window_count": model_alert_window_count,
        "model_alert": model_alert_window_count > 0,
        "alert_intervals": [
            {"start_seconds": start, "end_seconds": end}
            for start, end in (alert_intervals or [])
        ],
        "error_message": record.error_message,
        "model_name": model_metadata.get("model_name") if model_metadata else None,
        "model_version": model_metadata.get("model_version") if model_metadata else None,
        "score_type": model_metadata.get("score_type") if model_metadata else None,
    }
    if session is not None:
        canonical_profile = canonical_privacy_profile(methods_from_profile(session.privacy_method))
        payload.update({
            "session_id": session.session_id,
            "session_created_at": session.created_at.isoformat(),
            "privacy_method": canonical_profile,
            "privacy_methods": list(methods_from_profile(canonical_profile)),
        })
    return payload


def _public_session_payload(
    session: EEGSession,
    records: list[EEGRecording],
    alert_counts: dict[int, int],
    model_metadata: dict[int, dict[str, str]],
    alert_windows: dict[int, list],
) -> dict:
    """Build one session response from already-loaded summary data."""

    record_ids = [record.id for record in records if record.id is not None]
    completed_count = sum(record.status.value == "inferred" for record in records)
    failed_count = sum(record.status.value == "failed" for record in records)
    finished_count = completed_count + failed_count
    public_records = [
        public_record(
            record,
            model_alert_window_count=alert_counts.get(record.id or 0, 0),
            model_metadata=model_metadata.get(record.id or 0),
            alert_intervals=model_alert_intervals(alert_windows.get(record.id or 0, [])),
        )
        for record in records
    ]
    canonical_profile = canonical_privacy_profile(methods_from_profile(session.privacy_method))
    return {
        "session_id": session.session_id,
        "case_id": session.case_id,
        "privacy_method": canonical_profile,
        "privacy_methods": list(methods_from_profile(canonical_profile)),
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
            "model_alert_recordings": sum(alert_counts.get(record_id, 0) > 0 for record_id in record_ids),
        },
        "recordings": public_records,
    }


def public_session(db: Session, session: EEGSession, owner_user_id: int | None = None) -> dict:
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

    records = list_recordings_for_session(db, session.id, owner_user_id) if session.id is not None else []
    record_ids = [record.id for record in records if record.id is not None]
    return _public_session_payload(
        session,
        records,
        list_flagged_window_counts(db, record_ids),
        list_model_metadata(db, record_ids),
        list_flagged_prediction_windows(db, record_ids),
    )


def public_session_list(db: Session, owner_user_id: int | None = None) -> list[dict]:
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

    sessions = list_sessions(db, owner_user_id)
    session_ids = [session.id for session in sessions if session.id is not None]
    records = list_recordings_for_sessions(db, session_ids, owner_user_id)
    records_by_session: dict[int, list[EEGRecording]] = {}
    for record in records:
        records_by_session.setdefault(record.session_db_id, []).append(record)

    record_ids = [record.id for record in records if record.id is not None]
    alert_counts = list_flagged_window_counts(db, record_ids)
    model_metadata = list_model_metadata(db, record_ids)
    alert_windows = list_flagged_prediction_windows(db, record_ids)
    return [
        _public_session_payload(
            session,
            records_by_session.get(session.id or 0, []),
            alert_counts,
            model_metadata,
            alert_windows,
        )
        for session in sessions
    ]


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
