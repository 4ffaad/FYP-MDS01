"""Small database query layer used by services and API routes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, delete, func
from sqlmodel import Session, select

from backend.app.database.models.eeg import (
    EEGRecording,
    EEGSession,
    Explanation,
    Prediction,
    ProcessingAttempt,
    RecordingStatus,
    UploadDraft,
)


def get_upload_draft(db: Session, draft_id: str) -> UploadDraft | None:
    """Find one staged upload by its opaque draft identifier."""

    return db.exec(select(UploadDraft).where(UploadDraft.draft_id == draft_id)).first()


def list_expired_upload_drafts(db: Session, now: datetime) -> list[UploadDraft]:
    """Return staged uploads whose expiry time has passed."""

    return list(db.exec(select(UploadDraft).where(UploadDraft.expires_at <= now)).all())


def get_session_by_public_id(db: Session, session_id: str) -> EEGSession | None:
    """Find one session by its opaque public identifier."""

    return db.exec(select(EEGSession).where(EEGSession.session_id == session_id)).first()


def get_session_by_database_id(db: Session, session_db_id: int) -> EEGSession | None:
    """Find the owning session for one recording without exposing its database ID."""

    return db.get(EEGSession, session_db_id)


def list_sessions(db: Session) -> list[EEGSession]:
    """Return sessions ordered from newest to oldest."""

    return list(db.exec(select(EEGSession).order_by(EEGSession.created_at.desc())).all())


def get_recording_by_public_id(db: Session, record_id: str) -> EEGRecording | None:
    """Find one recording by its opaque public identifier."""

    return db.exec(select(EEGRecording).where(EEGRecording.record_id == record_id)).first()


def list_recordings_for_session(db: Session, session_db_id: int) -> list[EEGRecording]:
    """Return recordings for a session in archive sequence order."""

    statement = (
        select(EEGRecording)
        .where(EEGRecording.session_db_id == session_db_id)
        .order_by(EEGRecording.sequence_index)
    )
    return list(db.exec(statement).all())


def list_recordings_for_sessions(db: Session, session_db_ids: list[int]) -> list[EEGRecording]:
    """Return recordings for multiple sessions in stable archive order."""

    if not session_db_ids:
        return []
    statement = (
        select(EEGRecording)
        .where(EEGRecording.session_db_id.in_(session_db_ids))
        .order_by(EEGRecording.session_db_id, EEGRecording.sequence_index)
    )
    return list(db.exec(statement).all())


def list_predictions(db: Session, recording_db_id: int) -> list[Prediction]:
    """Return predictions only after the recording completed successfully."""

    statement = (
        select(Prediction)
        .join(EEGRecording, EEGRecording.id == Prediction.recording_db_id)
        .where(
            Prediction.recording_db_id == recording_db_id,
            EEGRecording.status == RecordingStatus.INFERRED,
        )
        .order_by(Prediction.window_index)
    )
    return list(db.exec(statement).all())


def list_predictions_for_processing(db: Session, recording_db_id: int) -> list[Prediction]:
    """Return private prediction rows while the processing transaction is active."""

    statement = (
        select(Prediction)
        .where(Prediction.recording_db_id == recording_db_id)
        .order_by(Prediction.window_index)
    )
    return list(db.exec(statement).all())


def list_explanations(db: Session, prediction_ids: list[int]) -> list[Explanation]:
    """Return explanation rows belonging to the supplied predictions."""

    if not prediction_ids:
        return []
    statement = select(Explanation).where(Explanation.prediction_db_id.in_(prediction_ids))
    return list(db.exec(statement).all())


def list_flagged_window_counts(db: Session, recording_ids: list[int]) -> dict[int, int]:
    """Count flagged model windows for each recording ID.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the aggregate query.
    recording_ids : list[int]
        Internal recording IDs whose safe alert counts are needed.

    Returns
    -------
    dict[int, int]
        Mapping from recording database ID to flagged-window count.
    """

    if not recording_ids:
        return {}
    counts = {recording_id: 0 for recording_id in recording_ids}
    rows = db.exec(
        select(Prediction.recording_db_id, func.count(Prediction.id))
        .join(EEGRecording, EEGRecording.id == Prediction.recording_db_id)
        .where(
            Prediction.recording_db_id.in_(recording_ids),
            Prediction.seizure_detected == True,  # noqa: E712
            EEGRecording.status == RecordingStatus.INFERRED,
        )
        .group_by(Prediction.recording_db_id)
    ).all()
    for recording_id, count in rows:
        counts[recording_id] = int(count)
    return counts


def list_flagged_prediction_windows(db: Session, recording_ids: list[int]) -> dict[int, list]:
    """Return positive timing rows for completed recordings in one bulk query."""

    if not recording_ids:
        return {}
    rows = db.exec(
        select(
            Prediction.recording_db_id,
            Prediction.start_seconds,
            Prediction.end_seconds,
            Prediction.seizure_detected,
        )
        .join(EEGRecording, EEGRecording.id == Prediction.recording_db_id)
        .where(
            Prediction.recording_db_id.in_(recording_ids),
            Prediction.seizure_detected == True,  # noqa: E712
            EEGRecording.status == RecordingStatus.INFERRED,
        )
        .order_by(Prediction.recording_db_id, Prediction.start_seconds, Prediction.end_seconds)
    ).all()
    windows: dict[int, list] = {}
    for row in rows:
        windows.setdefault(row.recording_db_id, []).append(row)
    return windows


def list_model_metadata(db: Session, recording_ids: list[int]) -> dict[int, dict[str, str]]:
    """Return safe model metadata for the first prediction of each recording.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    recording_ids : list[int]
        Internal recording IDs whose model metadata is needed.

    Returns
    -------
    dict[int, dict[str, str]]
        Model name, version, and score semantics keyed by recording ID.
    """

    if not recording_ids:
        return {}
    first_windows = (
        select(
            Prediction.recording_db_id,
            func.min(Prediction.window_index).label("first_window_index"),
        )
        .join(EEGRecording, EEGRecording.id == Prediction.recording_db_id)
        .where(
            Prediction.recording_db_id.in_(recording_ids),
            EEGRecording.status == RecordingStatus.INFERRED,
        )
        .group_by(Prediction.recording_db_id)
        .subquery()
    )
    rows = db.exec(
        select(
            Prediction.recording_db_id,
            Prediction.model_name,
            Prediction.model_version,
            Prediction.score_type,
        )
        .join(
            first_windows,
            and_(
                Prediction.recording_db_id == first_windows.c.recording_db_id,
                Prediction.window_index == first_windows.c.first_window_index,
            ),
        )
        .order_by(Prediction.recording_db_id)
    ).all()
    metadata: dict[int, dict[str, str]] = {}
    for recording_id, model_name, model_version, score_type in rows:
        metadata.setdefault(
            recording_id,
            {
                "model_name": model_name,
                "model_version": model_version,
                "score_type": score_type,
            },
        )
    return metadata


def delete_session_data(db: Session, session: EEGSession) -> None:
    """Delete one session and all dependent result and audit rows.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the deletion transaction.
    session : EEGSession
        Session row to remove. Its private files are deleted separately by
        the storage service.

    Raises
    ------
    Exception
        Database errors are propagated so the caller can report failure.
    """

    recordings = list_recordings_for_session(db, session.id or 0)
    recording_ids = [recording.id for recording in recordings if recording.id is not None]
    if recording_ids:
        prediction_ids = select(Prediction.id).where(Prediction.recording_db_id.in_(recording_ids))
        db.exec(delete(Explanation).where(Explanation.prediction_db_id.in_(prediction_ids)))
        db.exec(delete(Prediction).where(Prediction.recording_db_id.in_(recording_ids)))
        db.exec(delete(ProcessingAttempt).where(ProcessingAttempt.recording_db_id.in_(recording_ids)))
    db.exec(delete(ProcessingAttempt).where(ProcessingAttempt.session_db_id == session.id))
    db.exec(delete(EEGRecording).where(EEGRecording.session_db_id == session.id))
    db.delete(session)
    db.commit()
