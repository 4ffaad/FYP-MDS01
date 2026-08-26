"""Central authentication and response hardening for the FastAPI service."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Header, HTTPException, status
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

from backend.app.core.config import auth_configuration


def require_api_auth(
    assertion: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
) -> None:
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
    if not assertion:
        raise _unauthorized()

    try:
        signing_key = _jwk_client(domain).get_signing_key_from_jwt(assertion)
        jwt.decode(
            assertion,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"https://{domain}",
            options={"require": ["exp", "aud", "iss", "sub"]},
        )
    except (PyJWTError, PyJWKClientError, OSError) as exc:
        raise _unauthorized() from exc


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
