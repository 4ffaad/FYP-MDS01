"""Owner-scoped lookups; unowned legacy records can never match."""

from datetime import datetime

from sqlmodel import Session, select
from backend.app.database.models.video_detection import VideoDetectionJob


def get_job(db: Session, job_id: str, owner: int) -> VideoDetectionJob | None:
    return db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.job_id == job_id, VideoDetectionJob.owner_user_id == owner,
    )).first()


def list_jobs(db: Session, owner: int) -> list[VideoDetectionJob]:
    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.owner_user_id == owner,
    ).order_by(VideoDetectionJob.created_at.desc())).all())


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


def list_expired_jobs(db: Session, now: datetime) -> list[VideoDetectionJob]:
    """Return only non-terminal jobs whose retention window has elapsed."""

    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.status != "expired",
        VideoDetectionJob.retention_expires_at <= now,
    )).all())
