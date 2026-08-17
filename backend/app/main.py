"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.api.recordings import router as recordings_router
from backend.app.api.sessions import router as sessions_router


app = FastAPI(title="SeizureAI Backend", version="2.0.0")
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(recordings_router)
