"""Encrypted temporary upload-draft endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from backend.app.core.config import UPLOAD_DRAFT_TTL_SECONDS
from backend.app.core.security import owner_id, require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.repository import get_upload_draft
from backend.app.database.models.eeg import utc_now
from backend.app.services.session_service import (
    cleanup_expired_drafts,
    create_upload_draft,
    finalize_upload_draft,
)
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.processing_capacity import processing_capacity
from backend.app.privacy.methods import canonical_privacy_profile, normalize_privacy_methods


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _public_draft(draft) -> dict:
    """Serialize staged-upload metadata without exposing its storage path."""

    return {
        "draft_id": draft.draft_id,
        "status": "staged",
        "created_at": draft.created_at.isoformat(),
        "expires_at": draft.expires_at.isoformat(),
    }


@router.post("/drafts", status_code=status.HTTP_201_CREATED)
async def stage_upload(
    archive: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Encrypt a ZIP into a short-lived draft before privacy selection.

    Parameters
    ----------
    archive : fastapi.UploadFile
        ZIP archive containing EDF recordings.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        Opaque draft ID, status, and expiry timestamp.

    Raises
    ------
    fastapi.HTTPException
        Raised with 400 for invalid files or 503 for storage failures.
    """

    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload one ZIP archive containing EDF files.")
    storage = SessionStorage()
    cleanup_expired_drafts(db, storage)
    expires_at = utc_now() + timedelta(seconds=UPLOAD_DRAFT_TTL_SECONDS)
    try:
        draft = await create_upload_draft(db, storage, archive, expires_at, owner_id(current_user))
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _public_draft(draft)


@router.get("/drafts/{draft_id}")
def get_staged_upload(
    draft_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return safe status for one staged upload."""

    storage = SessionStorage()
    cleanup_expired_drafts(db, storage)
    draft = get_upload_draft(db, draft_id, owner_id(current_user))
    if draft is None:
        raise HTTPException(status_code=404, detail="Upload draft was not found or has expired.")
    return _public_draft(draft)


@router.post("/drafts/{draft_id}/finalize", status_code=status.HTTP_202_ACCEPTED)
def finalize_staged_upload(
    draft_id: str,
    background_tasks: BackgroundTasks,
    privacy_method: str | None = Form(None),
    privacy_methods: str | None = Form(None),
    case_id: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Create and queue one analysis session from an encrypted draft.

    Parameters
    ----------
    draft_id : str
        Opaque staged-upload identifier.
    privacy_method : str
        Supported method selected by the user.
    background_tasks : fastapi.BackgroundTasks
        FastAPI task registry used to start processing after the response.
    db : sqlmodel.Session
        Request-scoped database session.

    Returns
    -------
    dict
        HTTP 202 payload containing the new session ID.

    Raises
    ------
    fastapi.HTTPException
        Raised with 400 for unsupported methods, 404 for missing drafts, or
        503 when the staged archive cannot be promoted.
    """

    case_id = case_id if isinstance(case_id, str) and case_id else None
    try:
        selected_methods = normalize_privacy_methods(
            privacy_methods if isinstance(privacy_methods, str) else None,
            privacy_method if isinstance(privacy_method, str) else None,
        )
        privacy_profile = canonical_privacy_profile(selected_methods)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not processing_capacity.reserve():
        raise HTTPException(status_code=503, detail="The analysis service is at capacity. Try again later.")

    storage = SessionStorage()
    cleanup_expired_drafts(db, storage)
    try:
        finalize_kwargs = {}
        if (current_owner_id := owner_id(current_user)) is not None:
            finalize_kwargs["owner_user_id"] = current_owner_id
        if case_id:
            finalize_kwargs["case_id"] = case_id
        session = finalize_upload_draft(db, storage, draft_id, privacy_profile, **finalize_kwargs)
    except ValueError as exc:
        processing_capacity.release()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StorageError as exc:
        processing_capacity.release()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        processing_capacity.release()
        raise
    background_tasks.add_task(processing_capacity.run_reserved, session.session_id)
    return {"session_id": session.session_id, "case_id": session.case_id, "status": session.status.value}


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staged_upload(
    draft_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> None:
    """Delete one staged upload before it becomes an analysis session."""

    storage = SessionStorage()
    draft = get_upload_draft(db, draft_id, owner_id(current_user))
    if draft is None:
        raise HTTPException(status_code=404, detail="Upload draft was not found.")
    storage.delete_draft(draft.draft_id)
    db.delete(draft)
    db.commit()
