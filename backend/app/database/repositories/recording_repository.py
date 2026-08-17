"""Persistence operations for recordings and predictions."""

from sqlmodel import Session, select

from backend.app.database.models.eeg import EEGRecording, Prediction


def get_by_public_id(db: Session, record_id: str) -> EEGRecording | None:
    """Find one recording by its opaque public identifier.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    record_id : str
        Opaque recording identifier.

    Returns
    -------
    EEGRecording or None
        Matching row, or ``None`` when it does not exist.
    """

    return db.exec(select(EEGRecording).where(EEGRecording.record_id == record_id)).first()


def list_for_session(db: Session, session_db_id: int) -> list[EEGRecording]:
    """Return recordings for one database session in sequence order.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    session_db_id : int
        Internal primary key of the session.

    Returns
    -------
    list[EEGRecording]
        Recordings ordered by their archive sequence index.
    """

    return list(
        db.exec(
            select(EEGRecording)
            .where(EEGRecording.session_db_id == session_db_id)
            .order_by(EEGRecording.sequence_index)
        ).all()
    )


def list_predictions(db: Session, recording_db_id: int) -> list[Prediction]:
    """Return predictions for one recording in EEG time-window order.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session used for the query.
    recording_db_id : int
        Internal primary key of the recording.

    Returns
    -------
    list[Prediction]
        Window predictions ordered by their zero-based window index.
    """

    return list(
        db.exec(
            select(Prediction)
            .where(Prediction.recording_db_id == recording_db_id)
            .order_by(Prediction.window_index)
        ).all()
    )
