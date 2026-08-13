from fastapi import FastAPI

from app.api.records import router as records_router
from app.database.db import create_db_and_tables

app = FastAPI(title="EEG Privacy and Preprocessing API", version="1.0.0")

app.include_router(records_router)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the local prototype database schema exists."""
    create_db_and_tables()


@app.get("/health")
def health_check():
    """Confirm that the API process is running."""
    return {"status": "ok"}
