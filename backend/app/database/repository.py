"""Small database query layer used by services and API routes."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.app.database.models.eeg import (
    EEGRecording,
    EEGSession,
    Explanation,
    Prediction,
)


def get_session_by_public_id(db: Session, session_id: str) -> EEGSession | None:
    """Find one session by its opaque public identifier."""

    return db.exec(select(EEGSession).where(EEGSession.session_id == session_id)).first()


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
