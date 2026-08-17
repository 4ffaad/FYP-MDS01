"""Environment-driven backend configuration and storage paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BACKEND_ROOT / "storage"))).resolve()
SESSION_STORAGE_DIR = STORAGE_DIR / "sessions"
DATABASE_DIR = BACKEND_ROOT / "database"

# Docker supplies PostgreSQL. SQLite remains a small local fallback so unit
# tests and direct development imports work before containers are started.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATABASE_DIR / 'eeg.db'}",
)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
MAX_ARCHIVE_MEMBER_BYTES = int(
    os.getenv("MAX_ARCHIVE_MEMBER_BYTES", str(2 * 1024 * 1024 * 1024))
)
MAX_EDF_FILES_PER_ARCHIVE = int(os.getenv("MAX_EDF_FILES_PER_ARCHIVE", "500"))
ORIGINAL_RETENTION_DAYS = int(os.getenv("ORIGINAL_RETENTION_DAYS", "30"))
MODEL_RUNTIME = os.getenv("MODEL_RUNTIME", "stub")
MODEL_NAME = os.getenv("MODEL_NAME", "development-stub")
MODEL_VERSION = os.getenv("MODEL_VERSION", "stub-0.1.0")
MODEL_THRESHOLD = float(os.getenv("MODEL_THRESHOLD", "0.5"))


@dataclass(frozen=True)
class Settings:
    """Stable settings object for dependency injection and tests."""

    database_url: str = DATABASE_URL
    storage_dir: Path = STORAGE_DIR
    max_upload_bytes: int = MAX_UPLOAD_BYTES
    max_archive_member_bytes: int = MAX_ARCHIVE_MEMBER_BYTES
    max_edf_files_per_archive: int = MAX_EDF_FILES_PER_ARCHIVE
    original_retention_days: int = ORIGINAL_RETENTION_DAYS
    model_runtime: str = MODEL_RUNTIME
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION
    model_threshold: float = MODEL_THRESHOLD


settings = Settings()


def ensure_runtime_directories() -> None:
    """Create backend-owned directories required by local execution.

    Returns
    -------
    None
        The function creates the session-storage and local database parent
        directories if they do not already exist.
    """

    SESSION_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
