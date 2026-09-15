"""Session upload and status endpoints."""

from __future__ import annotations

from fastapi import BackgroundTasks, APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import Session

from backend.app.core.security import owner_id, require_api_auth
from backend.app.privacy.methods import canonical_privacy_profile, normalize_privacy_methods
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.services.session_service import (
    create_session,
    get_session_or_none,
    public_session,
    public_session_list,
    delete_session,
)
from backend.app.services.processing_capacity import processing_capacity
from backend.app.services.storage_service import SessionStorage, StorageError


router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_session(
    background_tasks: BackgroundTasks,
    archive: UploadFile = File(...),
    privacy_method: str = Form("metadata-scrub"),
    privacy_methods: str | None = Form(None),
    case_id: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Accept a ZIP archive, create a session, and schedule background work.

    Parameters
    ----------
    archive : fastapi.UploadFile
        ZIP archive containing one or more EDF recordings.
    privacy_method : str
        ``metadata-scrub`` or ``signal-obfuscation`` research privacy mode.
    background_tasks : fastapi.BackgroundTasks
        FastAPI-managed in-process task runner used to start the EEG pipeline
        after the HTTP response is sent.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        HTTP 202 payload containing the session ID and queued status.

    Raises
    ------
    fastapi.HTTPException
        Raised with 400 for invalid form input or 503 when storage is
        unavailable.
    """

    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload one ZIP archive containing EDF files.")
    case_id = case_id if isinstance(case_id, str) and case_id else None
    try:
        selected_methods = normalize_privacy_methods(
            privacy_methods if isinstance(privacy_methods, str) else None,
            privacy_method,
        )
        privacy_profile = canonical_privacy_profile(selected_methods)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not processing_capacity.reserve():
        raise HTTPException(status_code=503, detail="The analysis service is at capacity. Try again later.")

    try:
        create_kwargs = {}
        if (current_owner_id := owner_id(current_user)) is not None:
            create_kwargs["owner_user_id"] = current_owner_id
        if case_id:
            create_kwargs["case_id"] = case_id
        session = await create_session(db, SessionStorage(), archive, privacy_profile, **create_kwargs)
    except StorageError as exc:
        processing_capacity.release()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        processing_capacity.release()
        raise

    background_tasks.add_task(processing_capacity.run_reserved, session.session_id)
    payload = {
        "session_id": session.session_id,
        "status": session.status.value,
    }
    if session.case_id:
        payload["case_id"] = session.case_id
    return payload


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> list[dict]:
    """List sessions using privacy-safe public serialization.

    Parameters
    ----------
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    list[dict]
        Sessions ordered from newest to oldest without patient references.
    """

    return public_session_list(db, owner_id(current_user))


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return one session and its safe recording summaries.

    Parameters
    ----------
    session_id : str
        Opaque session identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Public session status, timestamps, and recording summaries.

    Raises
    ------
    fastapi.HTTPException
        Raised with 404 when the session does not exist.
    """

    session = get_session_or_none(db, session_id, owner_id(current_user))
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return public_session(db, session, owner_id(current_user))


@router.get("/sessions/{session_id}/status")
def get_session_status(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return the current pipeline stage and status for a session.

    Parameters
    ----------
    session_id : str
        Opaque session identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Current status, stage, and a safe error message when applicable.
    """

    session = get_session_or_none(db, session_id, owner_id(current_user))
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "current_stage": session.current_stage,
        "error_message": session.error_message,
    }


@router.get("/sessions/{session_id}/recordings")
def get_session_recordings(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> list[dict]:
    """List the safe recording summaries belonging to a session.

    Parameters
    ----------
    session_id : str
        Opaque session identifier.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    list[dict]
        Recording metadata without original filenames or storage paths.
    """

    session = get_session_or_none(db, session_id, owner_id(current_user))
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    return public_session(db, session, owner_id(current_user))["recordings"]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_route(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> Response:
    """Delete one completed session and its private artifacts.

    Parameters
    ----------
    session_id : str
        Opaque session identifier selected by the user.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    fastapi.Response
        Empty HTTP 204 response after database and private-storage cleanup.

    Raises
    ------
    fastapi.HTTPException
        Raised with 404 when missing or 409 while processing is active.
    """

    session = get_session_or_none(db, session_id, owner_id(current_user))
    if session is None:
        raise HTTPException(status_code=404, detail="Session was not found.")
    try:
        delete_session(db, SessionStorage(), session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
