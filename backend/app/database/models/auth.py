"""Persistent local-account and login-session records."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """One local account or externally authenticated workspace identity."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=64)
    email: str = Field(index=True, unique=True, max_length=320)
    password_hash: str | None = Field(default=None, max_length=256)
    auth_provider: str = Field(default="local", max_length=32)
    external_subject: str | None = Field(default=None, index=True, unique=True, max_length=256)
    display_name: str = Field(default="", max_length=80)
    active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    last_login_at: datetime | None = None


class AuthSession(SQLModel, table=True):
    """Server-side login session; only its hash is persisted."""

    __tablename__ = "auth_sessions"

    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True, max_length=64)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    revoked_at: datetime | None = None
