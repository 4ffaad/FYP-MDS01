"""FastAPI application entry point."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlmodel import Session

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.recordings import router as recordings_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.uploads import router as uploads_router
from backend.app.api.video_privacy import router as video_privacy_router
from backend.app.api.video_detection import router as video_detection_router
from backend.app.api.cases import router as cases_router
from backend.app.core.config import CLEANUP_INTERVAL_SECONDS, CORS_ORIGINS, MODEL_RUNTIME, auth_configuration
from backend.app.core.middleware import RequestBodyLimitMiddleware
from backend.app.core.security import require_api_auth
from backend.app.database.db import engine
from backend.app.ml.model_loader import get_inference_service
from backend.app.services.auth_service import ensure_demo_admin, purge_expired_auth_sessions
from backend.app.services.processing_service import eeg_retention_loop, sweep_interrupted_sessions
from backend.app.services.session_service import draft_retention_loop, sweep_expired_upload_drafts


LOGGER = logging.getLogger(__name__)


def _purge_auth_sessions() -> None:
    with Session(engine) as db:
        purge_expired_auth_sessions(db)


async def auth_session_retention_loop() -> None:
    """Periodically remove expired and revoked local-auth sessions."""

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(_purge_auth_sessions)
        except Exception:
            LOGGER.exception("Auth-session retention sweep failed.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Validate authentication and the selected model runtime before serving."""

    mode, _domain, _audience = auth_configuration()
    if mode == "local-accounts":
        with Session(engine) as db:
            ensure_demo_admin(db)
    await asyncio.to_thread(_purge_auth_sessions)
    if MODEL_RUNTIME == "h5":
        # Loading here makes a missing TensorFlow installation, artifact, or
        # reviewed contract fail at startup instead of after an upload returns
        # HTTP 202.
        get_inference_service()
    os.umask(0o077)
    from backend.app.services.video_detection_service import retention_loop, sweep
    from backend.app.services.video_privacy_service import (
        sweep_video_privacy_jobs,
        video_privacy_retention_loop,
    )
    # Migrations run before Uvicorn; recovery removes interrupted private work.
    # Tests that do not provision a database use their existing lifespan fixture.
    cleanup_tasks = []
    await asyncio.to_thread(sweep_interrupted_sessions)
    await asyncio.to_thread(sweep, startup=True)
    await asyncio.to_thread(sweep_video_privacy_jobs, startup=True)
    await asyncio.to_thread(sweep_expired_upload_drafts)
    cleanup_tasks.append(asyncio.create_task(eeg_retention_loop()))
    cleanup_tasks.append(asyncio.create_task(auth_session_retention_loop()))
    cleanup_tasks.append(asyncio.create_task(draft_retention_loop()))
    cleanup_tasks.append(asyncio.create_task(video_privacy_retention_loop()))
    if os.environ.get("VIDEO_DETECTION_ENABLED", "false").lower() == "true":
        cleanup_tasks.append(asyncio.create_task(retention_loop()))
    try:
        yield
    finally:
        for cleanup_task in cleanup_tasks:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


app = FastAPI(title="SeizureAI Backend", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    # Cloudflare Access authenticates browser requests with its secure cookie.
    # Explicit origins keep credentialed CORS narrow.
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.add_middleware(RequestBodyLimitMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Add browser hardening headers without changing response bodies."""

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Vary"] = "Cookie, Origin"
    if auth_configuration()[0] == "cloudflare":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(health_router)
app.include_router(auth_router)
api_dependencies = [Depends(require_api_auth)]
app.include_router(sessions_router, dependencies=api_dependencies)
app.include_router(recordings_router, dependencies=api_dependencies)
app.include_router(uploads_router, dependencies=api_dependencies)
app.include_router(video_privacy_router, dependencies=api_dependencies)
app.include_router(video_detection_router, dependencies=api_dependencies)
app.include_router(cases_router, dependencies=api_dependencies)


def custom_openapi() -> dict:
    """Expose the same authentication contract used by protected routers."""

    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema.setdefault("components", {})["securitySchemes"] = {
        "SessionCookie": {"type": "apiKey", "in": "cookie", "name": "mds01_session"},
        "CloudflareAccess": {
            "type": "apiKey",
            "in": "header",
            "name": "Cf-Access-Jwt-Assertion",
        },
    }
    public_paths = {
        "/api/auth/session",
        "/api/auth/register",
        "/api/auth/login",
    }
    for path, operations in schema.get("paths", {}).items():
        if not path.startswith("/api/") or path in public_paths:
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation["security"] = [
                    {"SessionCookie": []},
                    {"CloudflareAccess": []},
                ]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
