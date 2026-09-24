"""Protected endpoints for the standalone video privacy workflow."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from sqlmodel import Session

from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.core.security import mutation_owner_id, owner_id, require_api_auth
from backend.app.database.repository import get_video_job, list_video_jobs
from backend.app.services.video_privacy_service import (
    acknowledge_video_job,
    create_video_job,
    VideoPrivacyCapacityError,
    get_download_artifact,
    parse_profile,
    process_video_privacy_job,
    public_video_job,
)
from backend.app.services.video_storage_service import CleanupFileResponse, VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_privacy.processor import VideoProcessorError


router = APIRouter(prefix="/api/video-privacy", tags=["video-privacy"])


def _require_authenticated_user(current_user: User | None) -> User:
    """Reject the legacy ownerless development-auth mode for private video."""

    if not isinstance(current_user, User) or current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    profile: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Encrypt and queue one supported video privacy transform."""

    authenticated_user = _require_authenticated_user(current_user)
    try:
        selected_profile = parse_profile(profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    storage = VideoStorage()
    try:
        job = await create_video_job(
            db,
            storage,
            video,
            selected_profile,
            owner_user_id=authenticated_user.id,
        )
    except VideoPrivacyCapacityError as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "60"}) from exc
    except StorageError as exc:
        message = str(exc)
        code = 413 if "size" in message.lower() else 400
        raise HTTPException(status_code=code, detail="The video could not be stored securely within the configured limit.") from exc
    except VideoProcessorError as exc:
        code = 503 if "runtime" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail="The privacy transform could not process this video.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The video could not be secured for processing.") from exc
    background_tasks.add_task(process_video_privacy_job, job.job_id)
    return {"job": public_video_job(db, job)}


@router.get("/jobs")
def list_jobs(
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """List video privacy jobs without private media metadata."""

    _require_authenticated_user(current_user)
    storage = VideoStorage()
    return {"jobs": [public_video_job(db, job, storage) for job in list_video_jobs(db, owner_id(current_user))]}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return safe status and output policy for one job."""

    _require_authenticated_user(current_user)
    job = get_video_job(db, job_id, owner_id(current_user))
    if job is None:
        raise HTTPException(status_code=404, detail="Video privacy job was not found.")
    return {"job": public_video_job(db, job, VideoStorage())}


@router.post("/jobs/{job_id}/acknowledge")
def acknowledge_job(
    job_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Acknowledge a usable quality caveat before enabling download."""

    _require_authenticated_user(current_user)
    job = get_video_job(db, job_id, mutation_owner_id(current_user))
    if job is None:
        raise HTTPException(status_code=404, detail="Video privacy job was not found.")
    storage = VideoStorage()
    try:
        return {"job": public_video_job(db, acknowledge_video_job(db, job, storage), storage)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="The privacy acknowledgement is no longer available.") from exc



@router.get("/jobs/{job_id}/preview")
def get_preview(
    job_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> CleanupFileResponse:
    """Stream only the transformed representative preview frame."""

    _require_authenticated_user(current_user)
    storage = VideoStorage()
    try:
        job, encrypted_path = get_download_artifact(db, job_id, preview=True, storage=storage, owner_user_id=owner_id(current_user))
        materialized = storage.materialize_artifact(job.job_id, encrypted_path, f"protected-preview-{secrets.token_hex(8)}.jpg")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="The protected preview is not available.") from exc
    except (PermissionError, StorageError) as exc:
        raise HTTPException(status_code=409, detail="The protected preview is temporarily unavailable.") from exc
    return CleanupFileResponse(
        materialized,
        cleanup=lambda: storage.delete_work_file(materialized),
        media_type="image/jpeg",
        filename=f"protected-preview-{job.job_id}.jpg",
        headers={"Cache-Control": "no-store, private", "Pragma": "no-cache", "Vary": "Cookie, Origin"},
    )


@router.get("/jobs/{job_id}/download")
def download_output(
    job_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> CleanupFileResponse:
    """Stream transformed output only after backend policy checks pass."""

    _require_authenticated_user(current_user)
    storage = VideoStorage()
    try:
        job, encrypted_path = get_download_artifact(db, job_id, storage=storage, owner_user_id=owner_id(current_user))
        materialized = storage.materialize_artifact(job.job_id, encrypted_path, f"protected-output-{secrets.token_hex(8)}.mp4")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="The protected output is not available.") from exc
    except (PermissionError, StorageError) as exc:
        raise HTTPException(status_code=409, detail="The protected output is temporarily unavailable.") from exc
    return CleanupFileResponse(
        materialized,
        cleanup=lambda: storage.delete_work_file(materialized),
        media_type="video/mp4",
        filename=f"protected-video-{job.job_id}.mp4",
        headers={"Cache-Control": "no-store, private", "Pragma": "no-cache", "Vary": "Cookie, Origin"},
    )
