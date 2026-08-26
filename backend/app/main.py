"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.recordings import router as recordings_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.uploads import router as uploads_router
from backend.app.api.video_privacy import router as video_privacy_router
from backend.app.core.config import CORS_ORIGINS, MODEL_RUNTIME, auth_configuration
from backend.app.core.security import require_api_auth
from backend.app.ml.model_loader import get_inference_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Validate authentication and the selected model runtime before serving."""

    auth_configuration()
    if MODEL_RUNTIME == "h5":
        # Loading here makes a missing TensorFlow installation, artifact, or
        # reviewed contract fail at startup instead of after an upload returns
        # HTTP 202.
        get_inference_service()
    os.umask(0o077)
    yield


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


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Add browser hardening headers without changing response bodies."""

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if auth_configuration()[0] == "cloudflare":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(health_router)
api_dependencies = [Depends(require_api_auth)]
app.include_router(sessions_router, dependencies=api_dependencies)
app.include_router(recordings_router, dependencies=api_dependencies)
app.include_router(uploads_router, dependencies=api_dependencies)
app.include_router(video_privacy_router, dependencies=api_dependencies)
