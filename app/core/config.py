"""Application paths and upload limits.

Keeping these values in one place prevents API modules from relying on the
process working directory (which changes when the app is deployed).
"""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"
INCOMING_DIR = STORAGE_DIR / "incoming"
DEIDENTIFIED_DIR = STORAGE_DIR / "deidentified"
PROCESSED_DIR = STORAGE_DIR / "processed"
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_DIR / 'eeg.db'}")


def ensure_storage_directories() -> None:
    """Create the directories used for transient and generated files."""
    for directory in (INCOMING_DIR, DEIDENTIFIED_DIR, PROCESSED_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_database_directory() -> None:
    """Create the local SQLite parent directory when SQLite is in use."""
    if DATABASE_URL.startswith("sqlite:///"):
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
