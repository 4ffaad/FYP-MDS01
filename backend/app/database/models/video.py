"""Persistent, identifier-free metadata for standalone video privacy jobs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class VideoPrivacyProfile(str, Enum):
    """The only privacy transforms supported by the v1 video surface."""

    FACE_REDACTED = "face-redacted"
    POSE_ONLY = "pose-only"


class VideoPrivacyStatus(str, Enum):
    """Public-safe lifecycle states for a video privacy job."""

    QUEUED = "queued"
    PREFLIGHT = "preflight"
    PROCESSING = "processing"
    VALIDATING = "validating"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    EXPIRED = "expired"


class VideoPrivacyJob(SQLModel, table=True):
    """Metadata for one video transform; media stays in private storage."""

    __tablename__ = "video_privacy_jobs"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    job_id: str = Field(index=True, unique=True, max_length=64)
    profile: VideoPrivacyProfile = Field(
        sa_column=Column(
            SAEnum(VideoPrivacyProfile, native_enum=False, create_constraint=False),
            nullable=False,
            index=True,
        )
    )
    status: VideoPrivacyStatus = Field(
        default=VideoPrivacyStatus.QUEUED,
        sa_column=Column(
            SAEnum(VideoPrivacyStatus, native_enum=False, create_constraint=False),
            nullable=False,
            index=True,
        ),
    )
    display_label: str = Field(max_length=64)
    content_type: str = Field(default="video/mp4", max_length=64)
    file_size_bytes: int = Field(default=0, ge=0)
    duration_seconds: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    current_stage: str | None = Field(default=None, max_length=32)
    original_path: str | None = Field(default=None, max_length=1024)
    output_path: str | None = Field(default=None, max_length=1024)
    preview_path: str | None = Field(default=None, max_length=1024)
    quality_flags_json: str = Field(default="[]")
    output_usable: bool = False
    acknowledged_at: datetime | None = None
    retention_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    original_removed_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=256)

    def quality_flags(self) -> list[str]:
        """Decode persisted non-identifying quality flags."""

        try:
            flags = json.loads(self.quality_flags_json or "[]")
        except (TypeError, ValueError):
            return []
        if not isinstance(flags, list):
            return []
        return [flag for flag in flags if isinstance(flag, str)]
