"""Minimal audit trail for owner-authorized clinical data access."""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlmodel import Field, SQLModel

from backend.app.database.models.eeg import utc_now


class ClinicalAccessEvent(SQLModel, table=True):
    __tablename__ = "clinical_access_events"
    __table_args__ = (
        CheckConstraint(
            "(recording_db_id IS NOT NULL AND session_db_id IS NULL AND video_job_db_id IS NULL) OR "
            "(recording_db_id IS NULL AND session_db_id IS NOT NULL AND video_job_db_id IS NULL) OR "
            "(recording_db_id IS NULL AND session_db_id IS NULL AND video_job_db_id IS NOT NULL)",
            name="ck_clinical_access_events_one_resource",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
        ),
    )
    recording_db_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=True, index=True
        ),
    )
    session_db_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
        ),
    )
    video_job_db_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("video_detection_jobs.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    action: str = Field(sa_column=Column(String(40), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
