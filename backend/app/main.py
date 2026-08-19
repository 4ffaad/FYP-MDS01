"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.recordings import router as recordings_router
from backend.app.api.sessions import router as sessions_router
from backend.app.core.config import CORS_ORIGINS


app = FastAPI(title="SeizureAI Backend", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(recordings_router)
