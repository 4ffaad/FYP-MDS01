"""Opaque metadata pointing to one encrypted case source report."""

from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, Column, String
from sqlmodel import Field, SQLModel


class CaseSourceReport(SQLModel, table=True):
    """Owner-scoped pointer and crypto version; PDF bytes live only on disk."""

    __tablename__: Any = "case_source_reports"
    __table_args__ = (
        CheckConstraint(
            "artifact_id IS NOT NULL OR cleanup_artifact_id IS NOT NULL",
            name="ck_case_source_reports_has_artifact_pointer",
        ),
    )

    owner_user_id: int = Field(
        primary_key=True,
        foreign_key="users.id",
        index=True,
    )
    case_id: str = Field(primary_key=True, max_length=64)
    artifact_id: str | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    cleanup_artifact_id: str | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    crypto_version: int = Field(default=1, nullable=False)
