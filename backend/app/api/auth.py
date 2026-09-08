"""Public account and login-session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session

from backend.app.core.config import auth_configuration
from backend.app.core.security import (
    AUTH_COOKIE_NAME,
    require_request_origin,
    resolve_optional_user,
)
from backend.app.database.db import get_session
from backend.app.services.auth_service import (
    InvalidCredentials,
    SESSION_TTL,
    authenticate_local_user,
    public_user,
    register_user,
    revoke_session,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    """Email/password payload used by local account forms."""

    email: str
    password: str


def _require_local_accounts() -> None:
    if auth_configuration()[0] != "local-accounts":
        raise HTTPException(status_code=404, detail="Local account authentication is not enabled.")


def _set_session_cookie(request: Request, response: Response, raw_token: str) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        raw_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


@router.get("/session")
def get_auth_session(
    assertion: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_session),
) -> dict:
    """Return the current authentication state without exposing patient data."""

    user = resolve_optional_user(assertion, session_token, db)
    mode = auth_configuration()[0]
    return {"authenticated": mode == "local" or user is not None, "mode": mode, "user": public_user(user)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    credentials: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    """Register and sign in one local account."""

    _require_local_accounts()
    require_request_origin(request)
    try:
        user = register_user(db, credentials.email, credentials.password)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 422, detail=str(exc)) from exc
    # Registering a user creates no separate, unverified email workflow.
    _, raw_token = authenticate_local_user(db, user.email, credentials.password)
    _set_session_cookie(request, response, raw_token)
    return {"authenticated": True, "user": public_user(user)}


@router.post("/login")
def login(
    credentials: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    """Authenticate a local account and set its HttpOnly session cookie."""

    _require_local_accounts()
    require_request_origin(request)
    try:
        user, raw_token = authenticate_local_user(db, credentials.email, credentials.password)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    _set_session_cookie(request, response, raw_token)
    return {"authenticated": True, "user": public_user(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_session),
) -> Response:
    """Revoke the current session and remove its browser cookie."""

    _require_local_accounts()
    require_request_origin(request)
    revoke_session(db, session_token)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
