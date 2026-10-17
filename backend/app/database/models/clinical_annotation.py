"""Owner-scoped clinician observations linked to one EEG recording."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, LargeBinary
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClinicalAnnotation(SQLModel, table=True):
    __tablename__ = "clinical_annotations"

    id: int | None = Field(default=None, primary_key=True)
    annotation_id: str = Field(unique=True, max_length=64)
    recording_db_id: int = Field(
        foreign_key="recordings.id", index=True, ondelete="CASCADE"
    )
    owner_user_id: int = Field(foreign_key="users.id", index=True)
    created_by_user_id: int = Field(foreign_key="users.id", index=True)
    payload_nonce: bytes = Field(sa_column=Column(LargeBinary(12), nullable=False))
    payload_ciphertext: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    crypto_version: int = Field(default=1, nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
