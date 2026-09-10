"""Owner-scoped lookups; unowned legacy records can never match."""

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
