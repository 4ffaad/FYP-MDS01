"""Small database query layer used by services and API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import and_, delete, func, or_
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
from backend.app.database.models.video import VideoPrivacyJob, VideoPrivacyStatus


def get_upload_draft(
    db: Session,
    draft_id: str,
    owner_user_id: int | None = None,
    *,
    for_update: bool = False,
) -> UploadDraft | None:
    """Find one staged upload by its opaque draft identifier."""

    statement = select(UploadDraft).where(UploadDraft.draft_id == draft_id)
    if owner_user_id is not None:
        statement = statement.where(UploadDraft.owner_user_id == owner_user_id)
    if for_update:
        statement = statement.with_for_update()
    return db.exec(statement).first()


def list_upload_drafts_for_owner(db: Session, owner_user_id: int | None) -> list[UploadDraft]:
    """Return unexpired staged uploads belonging to one owner."""

    statement = select(UploadDraft).where(UploadDraft.expires_at > datetime.now(timezone.utc))
    if owner_user_id is None:
        statement = statement.where(UploadDraft.owner_user_id == None)  # noqa: E711
    else:
        statement = statement.where(UploadDraft.owner_user_id == owner_user_id)
    return list(db.exec(statement).all())


def list_upload_drafts(db: Session) -> list[UploadDraft]:
    """Return all staged uploads for retention reconciliation."""

    return list(db.exec(select(UploadDraft)).all())


def get_video_job(db: Session, job_id: str, owner_user_id: int | None = None) -> VideoPrivacyJob | None:
    """Find a video job by its opaque public identifier."""

    statement = select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
    if owner_user_id is not None:
        statement = statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    return db.exec(statement).first()


def list_video_jobs(db: Session, owner_user_id: int | None = None) -> list[VideoPrivacyJob]:
    """Return video jobs in newest-first order."""

    statement = select(VideoPrivacyJob).order_by(VideoPrivacyJob.created_at.desc())
    if owner_user_id is not None:
        statement = statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    return list(db.exec(statement).all())


def count_video_jobs(db: Session, owner_user_id: int | None = None) -> int:
    """Count video jobs without materializing their rows."""

    statement = select(func.count()).select_from(VideoPrivacyJob)
    if owner_user_id is not None:
        statement = statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    return int(db.exec(statement).one())


def _active_video_status_clause():
    """Build the active standalone privacy status predicate."""

    status_column = cast(Any, VideoPrivacyJob.status)
    return or_(
        status_column == VideoPrivacyStatus.QUEUED,
        status_column == VideoPrivacyStatus.PREFLIGHT,
        status_column == VideoPrivacyStatus.PROCESSING,
        status_column == VideoPrivacyStatus.VALIDATING,
    )


def count_active_video_jobs(db: Session) -> int:
    """Count all queued or running standalone privacy jobs."""

    return int(
        db.exec(
            select(func.count())
            .select_from(VideoPrivacyJob)
            .where(_active_video_status_clause())
        ).one()
    )


def count_active_video_jobs_for_owner(db: Session, owner_user_id: int | None) -> int:
    """Count active standalone privacy jobs for one owner."""

    statement = (
        select(func.count())
        .select_from(VideoPrivacyJob)
        .where(_active_video_status_clause())
    )
    if owner_user_id is None:
        statement = statement.where(VideoPrivacyJob.owner_user_id == None)  # noqa: E711
    else:
        statement = statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    return int(db.exec(statement).one())


def list_expired_upload_drafts(db: Session, now: datetime) -> list[UploadDraft]:
    """Return staged uploads whose expiry time has passed."""

    return list(db.exec(select(UploadDraft).where(UploadDraft.expires_at <= now)).all())


def get_session_by_public_id(db: Session, session_id: str, owner_user_id: int | None = None) -> EEGSession | None:
    """Find one session by its opaque public identifier."""

    statement = select(EEGSession).where(EEGSession.session_id == session_id)
    if owner_user_id is not None:
        statement = statement.where(EEGSession.owner_user_id == owner_user_id)
    return db.exec(statement).first()


def get_session_by_database_id(db: Session, session_db_id: int, owner_user_id: int | None = None) -> EEGSession | None:
    """Find the owning session for one recording without exposing its database ID."""

    session = db.get(EEGSession, session_db_id)
    if owner_user_id is not None and (session is None or session.owner_user_id != owner_user_id):
        return None
    return session


def list_sessions(db: Session, owner_user_id: int | None = None) -> list[EEGSession]:
    """Return sessions ordered from newest to oldest."""

    statement = select(EEGSession).order_by(EEGSession.created_at.desc())
    if owner_user_id is not None:
        statement = statement.where(EEGSession.owner_user_id == owner_user_id)
    return list(db.exec(statement).all())


def get_recording_by_public_id(db: Session, record_id: str, owner_user_id: int | None = None) -> EEGRecording | None:
    """Find one recording by its opaque public identifier."""

    statement = select(EEGRecording).where(EEGRecording.record_id == record_id)
    if owner_user_id is not None:
        statement = statement.join(EEGSession, EEGSession.id == EEGRecording.session_db_id).where(EEGSession.owner_user_id == owner_user_id)
    return db.exec(statement).first()


def list_recordings_for_session(db: Session, session_db_id: int, owner_user_id: int | None = None) -> list[EEGRecording]:
    """Return recordings for a session in archive sequence order."""

    statement = select(EEGRecording).where(EEGRecording.session_db_id == session_db_id)
    if owner_user_id is not None:
        statement = statement.join(EEGSession, EEGSession.id == EEGRecording.session_db_id).where(EEGSession.owner_user_id == owner_user_id)
    statement = statement.order_by(EEGRecording.sequence_index)
    return list(db.exec(statement).all())


def list_recordings_for_sessions(db: Session, session_db_ids: list[int], owner_user_id: int | None = None) -> list[EEGRecording]:
    """Return recordings for multiple sessions in stable archive order."""

    if not session_db_ids:
        return []
    statement = select(EEGRecording).where(EEGRecording.session_db_id.in_(session_db_ids))
    if owner_user_id is not None:
        statement = statement.join(EEGSession, EEGSession.id == EEGRecording.session_db_id).where(EEGSession.owner_user_id == owner_user_id)
    statement = statement.order_by(EEGRecording.session_db_id, EEGRecording.sequence_index)
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
