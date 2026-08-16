"""Asynchronous session upload and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from backend.app.database.db import get_session
from backend.app.services.session_service import (
    create_session,
    get_session_or_none,
    public_session,
    public_session_list,
)
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.workers.jobs import enqueue_pipeline


router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_session(
    archive: UploadFile = File(...),
    patient_reference: str = Form(...),
    db: Session = Depends(get_session),
) -> dict:
    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload one ZIP archive containing EDF files.")
    if not patient_reference.strip():
        raise HTTPException(status_code=400, detail="patient_reference is required.")

    try:
        session = await create_session(db, SessionStorage(), archive, patient_reference)
        job_id = enqueue_pipeline(session.session_id)
    except (StorageError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    session.job_id = job_id
    db.add(session)
    db.commit()
    return {
        "session_id": session.session_id,
        "job_id": job_id,
        "status": session.status.value,
    }


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_session)) -> list[dict]:
    return public_session_list(db)


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_session)) -> dict:
    session = get_session_or_none(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return public_session(db, session)


@router.get("/sessions/{session_id}/status")
def get_session_status(session_id: str, db: Session = Depends(get_session)) -> dict:
    session = get_session_or_none(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "current_stage": session.current_stage,
        "error_message": session.error_message,
    }


@router.get("/sessions/{session_id}/recordings")
def get_session_recordings(session_id: str, db: Session = Depends(get_session)) -> list[dict]:
    session = get_session_or_none(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return public_session(db, session)["recordings"]

