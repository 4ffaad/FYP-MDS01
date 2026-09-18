"""Environment-driven backend configuration and storage paths."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from backend.app.privacy.methods import SUPPORTED_PRIVACY_METHODS


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


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
def configured_cors_origins() -> tuple[str, ...]:
    """Return a validated CORS allowlist for the active deployment mode."""

    environment = os.getenv("APP_ENV", "development").strip().lower()
    raw_value = os.getenv("CORS_ORIGINS")
    if raw_value is None:
        raw_value = "http://localhost:3000,http://127.0.0.1:3000"
    origins = tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())
    if not origins:
        raise RuntimeError("CORS_ORIGINS must contain at least one explicit origin")

    for origin in origins:
        parsed = urlparse(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        if environment == "production" and (
            parsed.scheme != "https"
            or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise RuntimeError("production CORS_ORIGINS must be explicit HTTPS non-local origins")

    if environment == "production" and os.getenv("CORS_ORIGINS") is None:
        raise RuntimeError("production requires an explicit CORS_ORIGINS allowlist")
    return origins


CORS_ORIGINS = configured_cors_origins()
MAX_UPLOAD_BYTES = _positive_int("MAX_UPLOAD_BYTES", 2 * 1024 * 1024 * 1024)
MAX_ACTIVE_UPLOAD_DRAFTS = _positive_int("MAX_ACTIVE_UPLOAD_DRAFTS", 2)
MAX_PENDING_DRAFT_BYTES = int(
    os.getenv("MAX_PENDING_DRAFT_BYTES", str(MAX_UPLOAD_BYTES + 1024 * 1024))
)
if MAX_PENDING_DRAFT_BYTES <= 0:
    raise RuntimeError("MAX_PENDING_DRAFT_BYTES must be positive")
MAX_VIDEO_UPLOAD_BYTES = _positive_int("MAX_VIDEO_UPLOAD_BYTES", 512 * 1024 * 1024)
CLEANUP_INTERVAL_SECONDS = _positive_int("CLEANUP_INTERVAL_SECONDS", 60)
VIDEO_RETENTION_SECONDS = _positive_int("VIDEO_RETENTION_SECONDS", 24 * 60 * 60)
VIDEO_MAX_DURATION_SECONDS = _positive_int("VIDEO_MAX_DURATION_SECONDS", 3600)
VIDEO_MIN_FPS = _positive_float("VIDEO_MIN_FPS", 6)
VIDEO_MAX_FPS = _positive_float("VIDEO_MAX_FPS", 60)
VIDEO_MAX_WIDTH = _positive_int("VIDEO_MAX_WIDTH", 1920)
VIDEO_MAX_HEIGHT = _positive_int("VIDEO_MAX_HEIGHT", 1080)
VIDEO_MAX_FRAMES = _positive_int("VIDEO_MAX_FRAMES", 216000)
VIDEO_MAX_OUTPUT_BYTES = _positive_int("VIDEO_MAX_OUTPUT_BYTES", MAX_VIDEO_UPLOAD_BYTES * 2)
VIDEO_PRIVACY_TIMEOUT_SECONDS = _positive_float("VIDEO_PRIVACY_TIMEOUT_SECONDS", 900)
VIDEO_PREFLIGHT_TIMEOUT_SECONDS = _positive_float("VIDEO_PREFLIGHT_TIMEOUT_SECONDS", 30)
VIDEO_PRIVACY_MAX_ACTIVE_JOBS = _positive_int("VIDEO_PRIVACY_MAX_ACTIVE_JOBS", 4)
VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER = _positive_int("VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER", 1)
VIDEO_PRIVACY_MAX_CONCURRENT_JOBS = _positive_int("VIDEO_PRIVACY_MAX_CONCURRENT_JOBS", 1)
if VIDEO_MIN_FPS > VIDEO_MAX_FPS:
    raise RuntimeError("VIDEO_MIN_FPS cannot exceed VIDEO_MAX_FPS")
MAX_ARCHIVE_MEMBER_BYTES = _positive_int("MAX_ARCHIVE_MEMBER_BYTES", 2 * 1024 * 1024 * 1024)
MAX_EDF_FILES_PER_ARCHIVE = _positive_int("MAX_EDF_FILES_PER_ARCHIVE", 500)
MODEL_RUNTIME = os.getenv("MODEL_RUNTIME", "stub")
MODEL_NAME = os.getenv("MODEL_NAME", "development-stub")
MODEL_VERSION = os.getenv("MODEL_VERSION", "stub-0.1.0")
MODEL_THRESHOLD = float(os.getenv("MODEL_THRESHOLD", "0.5"))
H5_MODEL_PATH = Path(os.getenv("H5_MODEL_PATH", "/opt/eeg-model/best_seizure_model.h5"))
H5_CONTRACT_PATH = Path(os.getenv("H5_CONTRACT_PATH", "/opt/eeg-model/model-contract.json"))
H5_CONTRACT_SHA256 = os.getenv("H5_CONTRACT_SHA256", "").strip().lower()
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
    configured_cors_origins()
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production.")

    # Local account authentication is the safe default for development. The
    # unauthenticated compatibility mode exists only for isolated tests.
    mode = os.getenv("AUTH_MODE", "local-accounts").strip().lower()
    if mode not in {"local", "local-accounts", "cloudflare"}:
        raise RuntimeError("AUTH_MODE must be local, local-accounts, or cloudflare.")
    if environment == "production" and mode != "cloudflare":
        raise RuntimeError("AUTH_MODE must be cloudflare in production.")
    if mode == "local" and environment != "test":
        raise RuntimeError("AUTH_MODE=local is permitted only when APP_ENV=test.")

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

    os.umask(0o077)
    SESSION_STORAGE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    SESSION_STORAGE_DIR.chmod(0o700)

    if DATABASE_URL.startswith("sqlite:///"):
        DATABASE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        DATABASE_DIR.chmod(0o700)
        database_path = Path(DATABASE_URL.removeprefix("sqlite:///"))
        if database_path.exists():
            database_path.chmod(0o600)
