"""Small database query layer used by services and API routes."""

from __future__ import annotations

from sqlalchemy import delete
from sqlmodel import Session, select

from backend.app.database.models.eeg import (
    EEGRecording,
    EEGSession,
    Explanation,
    Prediction,
    ProcessingAttempt,
)


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


def list_predictions(db: Session, recording_db_id: int) -> list[Prediction]:
    """Return predictions for a recording in window order."""

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
    rows = db.exec(
        select(Prediction.recording_db_id, Prediction.id)
        .where(Prediction.recording_db_id.in_(recording_ids), Prediction.seizure_detected == True)  # noqa: E712
    ).all()
    counts = {recording_id: 0 for recording_id in recording_ids}
    for recording_id, _prediction_id in rows:
        counts[recording_id] = counts.get(recording_id, 0) + 1
    return counts


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
