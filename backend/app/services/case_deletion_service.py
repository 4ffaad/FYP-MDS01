"""Delete all owner-scoped data and retained files for one case."""

from __future__ import annotations

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from backend.app.database.models.eeg import AnalysisStatus, EEGSession
from backend.app.database.models.video import VideoPrivacyJob, VideoPrivacyStatus
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.database.repository import delete_sessions_data
from backend.app.services.case_profile_service import stage_patient_profile_deletion
from backend.app.services.case_service import CASE_ID_PATTERN, lock_owner_case_mutations
from backend.app.services.case_source_report_service import (
    CaseSourceReportError,
    delete_case_source_report,
)
from backend.app.services.storage_service import SessionStorage
from backend.app.services.video_storage_service import VideoStorage


class CaseDeletionNotFound(LookupError):
    """The case does not belong to the requesting owner."""


class CaseDeletionInProgress(ValueError):
    """At least one linked privacy or analysis job is still running."""


class CaseDeletionStorageError(RuntimeError):
    """Encrypted files could not be safely removed."""


_ACTIVE_EEG_STATUSES = frozenset(
    {
        AnalysisStatus.QUEUED,
        AnalysisStatus.VALIDATING,
        AnalysisStatus.DEIDENTIFYING,
        AnalysisStatus.PREPROCESSING,
        AnalysisStatus.INFERENCE,
        AnalysisStatus.EXPLAINING,
    }
)
_TERMINAL_PRIVACY_STATUSES = frozenset(
    {
        VideoPrivacyStatus.READY,
        VideoPrivacyStatus.NEEDS_REVIEW,
        VideoPrivacyStatus.FAILED,
        VideoPrivacyStatus.EXPIRED,
    }
)
_TERMINAL_DETECTION_STATUSES = frozenset({"ready", "failed", "expired"})


def delete_case(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
    eeg_storage: SessionStorage | None = None,
    video_storage: VideoStorage | None = None,
) -> None:
    """Remove a case's media, analysis rows, profile, and source report."""

    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise CaseDeletionNotFound

    lock_owner_case_mutations(db, owner_user_id)
    suffix = case_id[-8:]
    sessions = list(
        db.exec(
            select(EEGSession)
            .where(
                EEGSession.owner_user_id == owner_user_id,
                or_(
                    EEGSession.case_id == case_id,
                    and_(EEGSession.case_id.is_(None), EEGSession.session_id.endswith(suffix)),
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
    )
    detection_jobs = list(
        db.exec(
            select(VideoDetectionJob)
            .where(
                VideoDetectionJob.owner_user_id == owner_user_id,
                or_(
                    VideoDetectionJob.case_id == case_id,
                    and_(
                        VideoDetectionJob.case_id.is_(None),
                        VideoDetectionJob.job_id.endswith(suffix),
                    ),
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
    )
    privacy_jobs = list(
        db.exec(
            select(VideoPrivacyJob)
            .where(
                VideoPrivacyJob.owner_user_id == owner_user_id,
                or_(
                    VideoPrivacyJob.case_id == case_id,
                    and_(
                        VideoPrivacyJob.case_id.is_(None),
                        VideoPrivacyJob.job_id.endswith(suffix),
                    ),
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
    )
    if not sessions and not detection_jobs and not privacy_jobs:
        raise CaseDeletionNotFound

    if (
        any(session.status in _ACTIVE_EEG_STATUSES for session in sessions)
        or any(job.status not in _TERMINAL_DETECTION_STATUSES for job in detection_jobs)
        or any(job.status not in _TERMINAL_PRIVACY_STATUSES for job in privacy_jobs)
    ):
        raise CaseDeletionInProgress

    try:
        stage_patient_profile_deletion(
            db,
            case_id=case_id,
            owner_user_id=owner_user_id,
        )
    except Exception:
        db.rollback()
        raise

    eeg_storage = eeg_storage or SessionStorage()
    video_storage = video_storage or VideoStorage()
    try:
        for session in sessions:
            eeg_storage.delete_session(session.session_id)
        for job in (*detection_jobs, *privacy_jobs):
            video_storage.delete_job(job.job_id)
    except Exception as exc:
        db.rollback()
        raise CaseDeletionStorageError from exc

    try:
        delete_sessions_data(db, sessions, commit=False)
        for job in (*detection_jobs, *privacy_jobs):
            db.delete(job)
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        delete_case_source_report(db, case_id=case_id, owner_user_id=owner_user_id)
    except CaseSourceReportError as exc:
        raise CaseDeletionStorageError from exc
