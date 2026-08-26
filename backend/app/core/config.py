"""Environment-driven backend configuration and storage paths."""

from __future__ import annotations

import os
from pathlib import Path

from backend.app.privacy.methods import SUPPORTED_PRIVACY_METHODS


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
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
MAX_VIDEO_UPLOAD_BYTES = int(os.getenv("MAX_VIDEO_UPLOAD_BYTES", str(512 * 1024 * 1024)))
VIDEO_RETENTION_SECONDS = int(os.getenv("VIDEO_RETENTION_SECONDS", str(24 * 60 * 60)))
VIDEO_MAX_DURATION_SECONDS = int(os.getenv("VIDEO_MAX_DURATION_SECONDS", "3600"))
MAX_ARCHIVE_MEMBER_BYTES = int(
    os.getenv("MAX_ARCHIVE_MEMBER_BYTES", str(2 * 1024 * 1024 * 1024))
)
MAX_EDF_FILES_PER_ARCHIVE = int(os.getenv("MAX_EDF_FILES_PER_ARCHIVE", "500"))
MODEL_RUNTIME = os.getenv("MODEL_RUNTIME", "stub")
MODEL_NAME = os.getenv("MODEL_NAME", "development-stub")
MODEL_VERSION = os.getenv("MODEL_VERSION", "stub-0.1.0")
MODEL_THRESHOLD = float(os.getenv("MODEL_THRESHOLD", "0.5"))
H5_MODEL_PATH = Path(os.getenv("H5_MODEL_PATH", str(BACKEND_ROOT / "model" / "best_seizure_model.h5")))
H5_CONTRACT_PATH = Path(os.getenv("H5_CONTRACT_PATH", str(BACKEND_ROOT / "model" / "model-contract.json")))
SIGNAL_RETENTION_CONTEXT_SECONDS = float(os.getenv("SIGNAL_RETENTION_CONTEXT_SECONDS", "600"))
UPLOAD_DRAFT_TTL_SECONDS = int(os.getenv("UPLOAD_DRAFT_TTL_SECONDS", "1800"))
ENABLE_SIGNAL_PREVIEW = os.getenv("ENABLE_SIGNAL_PREVIEW", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
ENABLE_FULL_SIGNAL_PREVIEW = (
    os.getenv("ENABLE_FULL_SIGNAL_PREVIEW", "false").lower() == "true"
    and APP_ENV in {"development", "test"}
)
FULL_SIGNAL_PREVIEW_MAX_SECONDS = float(os.getenv("FULL_SIGNAL_PREVIEW_MAX_SECONDS", "7200"))
ENABLE_SHAP_EXPLANATIONS = os.getenv("ENABLE_SHAP_EXPLANATIONS", "false").lower() == "true"
SHAP_METADATA_BACKGROUND_PATH = Path(
    os.getenv(
        "SHAP_METADATA_BACKGROUND_PATH",
        str(BACKEND_ROOT / "model" / "shap-background-metadata.npy"),
    )
)
SHAP_OBFUSCATED_BACKGROUND_PATH = Path(
    os.getenv(
        "SHAP_OBFUSCATED_BACKGROUND_PATH",
        str(BACKEND_ROOT / "model" / "shap-background-obfuscated.npy"),
    )
)
SHAP_MAX_WINDOWS = int(os.getenv("SHAP_MAX_WINDOWS", "3"))
SHAP_TIME_BINS = int(os.getenv("SHAP_TIME_BINS", "32"))
STORAGE_KEY_ENV = "MDS01_STORAGE_KEY"
TEMPLATE_KEY_ENV = "MDS01_TEMPLATE_KEY"


def auth_configuration() -> tuple[str, str, str]:
    """Return and validate the active API authentication configuration.

    Returns
    -------
    tuple[str, str, str]
        Authentication mode, Cloudflare Access team domain, and audience.

    Raises
    ------
    RuntimeError
        Raised when the mode is unsupported or Cloudflare configuration is
        incomplete or unsafe.
    """

    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production.")

    mode = os.getenv("AUTH_MODE", "local").strip().lower()
    if mode not in {"local", "cloudflare"}:
        raise RuntimeError("AUTH_MODE must be local or cloudflare.")
    if environment == "production" and mode != "cloudflare":
        raise RuntimeError("AUTH_MODE must be cloudflare in production.")

    domain = os.getenv("CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip().lower()
    audience = os.getenv("CLOUDFLARE_ACCESS_AUD", "").strip()
    if mode == "cloudflare":
        if (
            not domain.endswith(".cloudflareaccess.com")
            or "://" in domain
            or "/" in domain
            or not audience
        ):
            raise RuntimeError(
                "Cloudflare Access requires a valid team domain and audience."
            )

    return mode, domain, audience


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
