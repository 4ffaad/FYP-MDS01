"""Video detection metadata; source media and predictions remain encrypted."""

from datetime import datetime
from sqlmodel import Field, SQLModel
from backend.app.database.models.video import utc_now


class VideoDetectionJob(SQLModel, table=True):
    __tablename__ = "video_detection_jobs"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="users.id", index=True)
    job_id: str = Field(unique=True, index=True, max_length=64)
    status: str = Field(default="queued", max_length=32)
    current_stage: str = Field(default="preflight", max_length=32)
    duration_seconds: float = 0
    fps: float = 0
    original_path: str | None = None
    video_path: str | None = None
    predictions_path: str | None = None
    error_code: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    retention_expires_at: datetime
