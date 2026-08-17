"""Persistence operations for analysis sessions."""

from sqlmodel import Session, select

from backend.app.database.models.eeg import EEGSession


def get_by_public_id(db: Session, session_id: str) -> EEGSession | None:
    """Find one session by its opaque public identifier.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    session_id : str
        Opaque session identifier.

    Returns
    -------
    EEGSession or None
        Matching row, or ``None`` when it does not exist.
    """

    return db.exec(select(EEGSession).where(EEGSession.session_id == session_id)).first()


def list_sessions(db: Session) -> list[EEGSession]:
    """Return sessions ordered from newest to oldest.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.

    Returns
    -------
    list[EEGSession]
        All session rows ordered by creation time descending.
    """

    return list(db.exec(select(EEGSession).order_by(EEGSession.created_at.desc())).all())
