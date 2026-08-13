"""SQLModel database setup isolated from API and service code."""

from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

from app.core.config import DATABASE_URL, ensure_database_directory


ensure_database_directory()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def create_db_and_tables() -> None:
    """Create the prototype schema and apply its one lightweight upgrade."""
    SQLModel.metadata.create_all(engine)
    # ``create_all`` never changes an existing SQLite table.  This small,
    # idempotent upgrade adds the preprocessed output reference to databases
    # created before that field existed.  Use Alembic once the schema settles.
    if DATABASE_URL.startswith("sqlite"):
        columns = {column["name"] for column in inspect(engine).get_columns("eegrecording")}
        if "preprocessed_path" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE eegrecording ADD COLUMN preprocessed_path VARCHAR"))


def get_session() -> Generator[Session, None, None]:
    """Provide one database session per FastAPI request."""
    with Session(engine) as session:
        yield session
