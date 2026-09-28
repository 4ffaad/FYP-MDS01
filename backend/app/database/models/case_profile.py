"""Encrypted owner-scoped patient identity and extracted report profile."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, LargeBinary, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return an aware UTC timestamp for profile creation and audit metadata."""

    return datetime.now(timezone.utc)


class CasePatientProfile(SQLModel, table=True):
    """Owner-scoped encrypted name and hospital ID for one analysis case."""

    __tablename__ = "case_patient_profiles"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "case_id",
            name="uq_case_patient_profiles_owner_case",
        ),
        CheckConstraint(
            "verification_status IN ('reviewed', 'auto_extracted')",
            name="ck_case_patient_profiles_verification_status",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    case_id: str = Field(index=True, max_length=64)
    owner_user_id: int = Field(foreign_key="users.id", index=True)
    identity_nonce: bytes = Field(sa_column=Column(LargeBinary(12), nullable=False))
    identity_ciphertext: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    crypto_version: int = Field(default=1, nullable=False)
    verification_status: str = Field(default="reviewed", max_length=24, nullable=False)
    reviewed_by_user_id: int | None = Field(
        default=None,
        foreign_key="users.id",
        nullable=True,
    )
    reviewed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
