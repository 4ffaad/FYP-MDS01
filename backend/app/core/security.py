"""Central authentication and response hardening for the FastAPI service."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

from sqlmodel import Session

from backend.app.core.config import CORS_ORIGINS, auth_configuration
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.services.auth_service import InvalidCredentials, cloudflare_user, user_for_session


AUTH_COOKIE_NAME = "mds01_session"


def require_api_auth(
    request: Request,
    assertion: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_session),
) -> User | None:
    """Allow local requests or verify a Cloudflare Access assertion.

    Parameters
    ----------
    assertion : str | None
        JWT inserted by Cloudflare Access after successful authentication.

    Raises
    ------
    fastapi.HTTPException
        Raised with HTTP 401 when the assertion is absent or invalid.
    RuntimeError
        Raised when authentication configuration is invalid.
    """

    mode, domain, audience = auth_configuration()
    if mode == "local":
        return
    if mode == "local-accounts":
        if request.method in {"POST", "DELETE", "PUT", "PATCH"}:
            require_request_origin(request)
        user = user_for_session(db, session_token)
        if user is None:
            raise _unauthorized()
        return user
    if not assertion:
        raise _unauthorized()

    try:
        claims = verify_cloudflare_assertion(assertion, domain, audience)
        return cloudflare_user(db, claims)
    except (InvalidCredentials, PyJWTError, PyJWKClientError, OSError) as exc:
        raise _unauthorized() from exc


def resolve_optional_user(
    assertion: str | None,
    session_token: str | None,
    db: Session,
) -> User | None:
    """Resolve a session for the public auth-status endpoint."""

    mode, domain, audience = auth_configuration()
    if mode == "local":
        return None
    if mode == "local-accounts":
        return user_for_session(db, session_token)
    if not assertion:
        return None
    try:
        return cloudflare_user(db, verify_cloudflare_assertion(assertion, domain, audience))
    except (InvalidCredentials, PyJWTError, PyJWKClientError, OSError):
        return None


def verify_cloudflare_assertion(assertion: str, domain: str, audience: str) -> dict[str, object]:
    """Verify a Cloudflare Access JWT and return its claims."""

    signing_key = _jwk_client(domain).get_signing_key_from_jwt(assertion)
    return jwt.decode(
        assertion,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=f"https://{domain}",
        options={"require": ["exp", "aud", "iss", "sub"]},
    )


def require_request_origin(request: Request) -> None:
    """Require browser state changes to originate from the configured UI."""

    if request.headers.get("origin") not in CORS_ORIGINS:
        raise HTTPException(status_code=403, detail="The request origin is not allowed.")


def owner_id(user: User | None) -> int | None:
    """Return an internal owner key, or None for explicit local test mode."""

    return user.id if isinstance(user, User) else None


@lru_cache(maxsize=4)
def _jwk_client(domain: str) -> PyJWKClient:
    """Reuse Cloudflare signing-key caches for each configured team domain."""

    return PyJWKClient(f"https://{domain}/cdn-cgi/access/certs")


def _unauthorized() -> HTTPException:
    """Build the API's non-disclosing authentication failure response."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
