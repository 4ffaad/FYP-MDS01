"""SQLModel engine and session utilities."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.config import DATABASE_URL, ensure_runtime_directories


ensure_runtime_directories()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Compatibility helper for local prototype callers.

    Production startup uses Alembic. This helper is intentionally not called
    by FastAPI startup, but remains useful for isolated local tests.
    """

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

