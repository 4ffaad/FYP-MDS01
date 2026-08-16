"""Persistence operations for analysis sessions."""

from sqlmodel import Session, select

from backend.app.database.models.eeg import EEGSession


def get_by_public_id(db: Session, session_id: str) -> EEGSession | None:
    return db.exec(select(EEGSession).where(EEGSession.session_id == session_id)).first()


def list_sessions(db: Session) -> list[EEGSession]:
    return list(db.exec(select(EEGSession).order_by(EEGSession.created_at.desc())).all())

