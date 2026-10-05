"""Video detection metadata; source media and predictions remain encrypted."""

from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, LargeBinary
from sqlmodel import Field, SQLModel
from backend.app.database.models.video import utc_now


class VideoDetectionJob(SQLModel, table=True):
    __tablename__ = "video_detection_jobs"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="users.id", index=True)
    job_id: str = Field(unique=True, index=True, max_length=64)
    case_id: str | None = Field(default=None, index=True, max_length=64)
    status: str = Field(default="queued", max_length=32)
    current_stage: str = Field(default="preflight", max_length=32)
    review_privacy_method: str = Field(
        default="tracked-face-blur-with-full-frame-fallback", max_length=64
    )
    blur_strength_percent: int = Field(default=100, ge=50, le=100)
    source_name_token: str | None = Field(default=None, max_length=64, index=True)
    source_group_id: str | None = Field(default=None, max_length=36, index=True)
    sync_group_complete: bool = False
    eeg_recording_db_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("recordings.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    eeg_sync_status: str = Field(default="unavailable", max_length=24)
    eeg_sync_nonce: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )
    eeg_sync_ciphertext: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )
    duration_seconds: float = 0
    fps: float = 0
    original_path: str | None = None
    video_path: str | None = None
    visualization_path: str | None = None
    predictions_path: str | None = None
    error_code: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    retention_expires_at: datetime
