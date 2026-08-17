"""SQLModel engine and session utilities."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, create_engine

from backend.app.core.config import DATABASE_URL, ensure_runtime_directories


ensure_runtime_directories()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    """Yield one database session for the lifetime of an API request.

    Yields
    ------
    sqlmodel.Session
        A session bound to the configured database engine. The context
        manager closes it after the request or background operation completes.
    """

    with Session(engine) as session:
        yield session
