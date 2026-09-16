"""Small server-side account and session service for local demonstrations."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from backend.app.database.models.auth import AuthSession, User


MIN_PASSWORD_LENGTH = 8
DEMO_ADMIN_PUBLIC_ID = "USR-DEMO-ADMIN"
DEFAULT_DEMO_ADMIN_EMAIL = "admin@mds01.local"
DEFAULT_DEMO_ADMIN_PASSWORD = "12345678"
SESSION_TTL = timedelta(hours=8)
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64


class InvalidCredentials(ValueError):
    """Raised when a local login cannot be authenticated."""


def normalize_email(value: str) -> str:
    """Normalize and minimally validate the account identifier."""

    email = value.strip().casefold()
    if len(email) > 320 or any(character.isspace() for character in email) or "@" not in email:
        raise ValueError("Enter a valid email address.")
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("Enter a valid email address.")
    return email


def validate_password(password: str) -> None:
    """Enforce the prototype's minimum password length."""

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def hash_password(password: str) -> str:
    """Hash a password with a salted, standard-library scrypt record."""

    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encode(salt)}${encode(digest)}"


def verify_password(password: str, encoded: str | None) -> bool:
    """Verify a stored scrypt record without revealing malformed hashes."""

    if not encoded:
        return False
    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def _new_user_id() -> str:
    return f"USR-{secrets.token_hex(16).upper()}"


def register_user(db: Session, email: str, password: str) -> User:
    """Create one local account, rejecting duplicate identifiers."""

    normalized_email = normalize_email(email)
    validate_password(password)
    if db.exec(select(User).where(User.email == normalized_email)).first() is not None:
        raise ValueError("An account with that email already exists.")
    user = User(
        public_id=_new_user_id(),
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=normalized_email.split("@", 1)[0][:80],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_demo_admin(db: Session) -> User | None:
    """Create the local demo administrator only in development mode."""

    if (
        os.getenv("APP_ENV", "development").strip().lower() != "development"
        or os.getenv("AUTH_MODE", "local").strip().lower() != "local-accounts"
        or os.getenv("DEMO_ADMIN_ENABLED", "true").strip().lower() != "true"
    ):
        return None

    email = normalize_email(os.getenv("DEMO_ADMIN_EMAIL", DEFAULT_DEMO_ADMIN_EMAIL))
    password = os.getenv("DEMO_ADMIN_PASSWORD", DEFAULT_DEMO_ADMIN_PASSWORD)
    validate_password(password)
    user = db.exec(select(User).where(User.email == email)).first()
    if user is not None:
        if user.public_id == DEMO_ADMIN_PUBLIC_ID and not user.is_admin:
            user.is_admin = True
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(
        public_id=DEMO_ADMIN_PUBLIC_ID,
        email=email,
        password_hash=hash_password(password),
        auth_provider="local",
        display_name="admin",
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_local_user(db: Session, email: str, password: str) -> tuple[User, str]:
    """Authenticate a local account and issue an opaque raw session token."""

    try:
        normalized_email = normalize_email(email)
    except ValueError as exc:
        raise InvalidCredentials("Email or password is incorrect.") from exc
    user = db.exec(select(User).where(User.email == normalized_email, User.auth_provider == "local")).first()
    if user is None or not user.active or not verify_password(password, user.password_hash):
        raise InvalidCredentials("Email or password is incorrect.")
    raw_token = secrets.token_urlsafe(32)
    auth_session = AuthSession(
        token_hash=token_hash(raw_token),
        user_id=user.id or 0,
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.add(auth_session)
    db.add(user)
    db.commit()
    return user, raw_token


def token_hash(raw_token: str) -> str:
    """Hash a cookie token before it reaches persistent storage."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def user_for_session(db: Session, raw_token: str | None) -> User | None:
    """Return the active user for an unexpired, non-revoked session."""

    if not raw_token:
        return None
    session = db.exec(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token))).first()
    if session is None or session.revoked_at is not None or _expired(session.expires_at):
        return None
    user = db.get(User, session.user_id)
    return user if user is not None and user.active else None


def revoke_session(db: Session, raw_token: str | None) -> None:
    """Invalidate a cookie token if it belongs to a stored session."""

    if raw_token:
        session = db.exec(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token))).first()
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.add(session)
            db.commit()


def cloudflare_user(db: Session, claims: dict[str, object]) -> User:
    """Map a verified Cloudflare subject to a stable local ownership row."""

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidCredentials("Authentication subject is missing.")
    user = db.exec(select(User).where(User.external_subject == subject)).first()
    if user is not None:
        return user
    claim_email = claims.get("email")
    email = claim_email.strip().casefold() if isinstance(claim_email, str) and claim_email.strip() else f"cloudflare:{subject}"
    existing = db.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise InvalidCredentials("This account is already linked to another identity.")
    user = User(
        public_id=_new_user_id(),
        email=email[:320],
        auth_provider="cloudflare",
        external_subject=subject,
        display_name=email.split("@", 1)[0][:80],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def public_user(user: User | None) -> dict | None:
    """Serialize only the account fields needed by the workspace header."""

    if user is None:
        return None
    return {"id": user.public_id, "email": user.email, "display_name": user.display_name}


def _expired(value: datetime) -> bool:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized <= datetime.now(timezone.utc)
