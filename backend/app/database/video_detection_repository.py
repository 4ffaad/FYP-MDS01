"""Owner-scoped lookups; unowned legacy records can never match."""

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


def count_active_jobs(db: Session) -> int:
    return len(
        db.exec(
            select(VideoDetectionJob.id).where(
                VideoDetectionJob.status.in_(("queued", "processing")),
            )
        ).all()
    )


def get_next_queued_job(db: Session) -> VideoDetectionJob | None:
    created_at = getattr(VideoDetectionJob, "created_at")
    return db.exec(
        select(VideoDetectionJob)
        .where(VideoDetectionJob.status == "queued")
        .order_by(created_at, VideoDetectionJob.id)
    ).first()


def list_all_jobs_for_cleanup(db: Session) -> list[VideoDetectionJob]:
    """Return every job so failed expiry cleanup can be retried."""

    return list(db.exec(select(VideoDetectionJob)).all())


def list_ready_jobs(db: Session) -> list[VideoDetectionJob]:
    return list(db.exec(select(VideoDetectionJob).where(
        VideoDetectionJob.status == "ready",
    )).all())
