"""Persistence operations for recordings and predictions."""

from sqlmodel import Session, select

from backend.app.database.models.eeg import EEGRecording, Prediction


def get_by_public_id(db: Session, record_id: str) -> EEGRecording | None:
    return db.exec(select(EEGRecording).where(EEGRecording.record_id == record_id)).first()


def list_for_session(db: Session, session_db_id: int) -> list[EEGRecording]:
    return list(
        db.exec(
            select(EEGRecording)
            .where(EEGRecording.session_db_id == session_db_id)
            .order_by(EEGRecording.sequence_index)
        ).all()
    )


def list_predictions(db: Session, recording_db_id: int) -> list[Prediction]:
    return list(
        db.exec(
            select(Prediction)
            .where(Prediction.recording_db_id == recording_db_id)
            .order_by(Prediction.window_index)
        ).all()
    )

