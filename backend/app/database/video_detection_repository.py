"""Owner-scoped lookups; unowned legacy records can never match."""

from datetime import datetime

from sqlalchemy import desc
from sqlmodel import Session, select
from backend.app.database.models.video_detection import VideoDetectionJob


def get_job(db: Session, job_id: str, owner: int | None) -> VideoDetectionJob | None:
    statement = select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)
    if owner is not None:
        statement = statement.where(VideoDetectionJob.owner_user_id == owner)
    return db.exec(statement).first()


def list_jobs(db: Session, owner: int | None) -> list[VideoDetectionJob]:
    statement = select(VideoDetectionJob)
    if owner is not None:
        statement = statement.where(VideoDetectionJob.owner_user_id == owner)
    created_at = getattr(VideoDetectionJob, "created_at")
    return list(db.exec(statement.order_by(desc(created_at))).all())


def has_active_job(db: Session) -> bool:
    return db.exec(select(VideoDetectionJob.id).where(
        VideoDetectionJob.status.in_(("queued", "processing")),
    )).first() is not None


def get_queued_job(db: Session, job_id: str) -> VideoDetectionJob | None:
    return db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.job_id == job_id, VideoDetectionJob.status == "queued",
    )).first()


def list_unexpired_jobs(db: Session) -> list[VideoDetectionJob]:
    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.status != "expired",
    )).all())


def list_all_jobs_for_cleanup(db: Session) -> list[VideoDetectionJob]:
    """Return every job so failed expiry cleanup can be retried."""

    return list(db.exec(select(VideoDetectionJob)).all())


def list_expired_jobs(db: Session, now: datetime) -> list[VideoDetectionJob]:
    """Return only non-terminal jobs whose retention window has elapsed."""

    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.status != "expired",
        VideoDetectionJob.retention_expires_at <= now,
    )).all())


def list_ready_jobs(db: Session) -> list[VideoDetectionJob]:
    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.status == "ready",
    )).all())
