"""Authenticated video detection and owner-scoped results."""

import asyncio
import json
import os
from pathlib import Path
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from sqlmodel import Session

from backend.app.core.security import owner_id, require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database import video_detection_repository as repository
from backend.app.services.case_service import CaseReferenceError
from backend.app.services import video_detection_service as service
from backend.app.services.video_storage_service import CleanupFileResponse, VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_detection.contract import DetectionError

router = APIRouter(prefix="/api/video-detection", tags=["video-detection"])


def account(user: User | None = Depends(require_api_auth)) -> User:
    if user is None or user.id is None:
        raise HTTPException(401, "Sign in to use video detection.")
    return user


def scoped_owner(user: User) -> int | None:
    """Return the shared owner filter for detection reads."""

    return owner_id(user)


def owned(job_id, owner, db, storage):
    job = repository.get_job(db, job_id, owner)
    if job is None:
        raise HTTPException(404, "Video detection job was not found.")
    return service.expire_job(db, job, storage)


@router.post("/jobs", status_code=202)
async def create(background_tasks: BackgroundTasks, video: UploadFile = File(...),
                 case_id: str | None = Form(None),
                 current_user: User = Depends(account), db: Session = Depends(get_session)):
    case_id = case_id if isinstance(case_id, str) and case_id else None
    owner = current_user.id
    if owner is None:
        raise HTTPException(401, "Sign in to use video detection.")
    try:
        if os.environ.get("VIDEO_DETECTION_ENABLED", "false").lower() != "true":
            raise HTTPException(503, "Enable the local video detection runtime using the setup guide.")
        async with service.UPLOAD_LOCK:
            if repository.has_active_job(db):
                raise HTTPException(409, "A video is already processing. Try again after it finishes.")
            job = (
                await service.create_job(db, VideoStorage(), video, current_user.id, case_id)
                if case_id
                else await service.create_job(db, VideoStorage(), video, current_user.id)
            )
        background_tasks.add_task(service.process_job, job.job_id)
        return {"job": service.public_job(db, job, VideoStorage())}
    except CaseReferenceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except DetectionError as exc:
        raise HTTPException(422 if str(exc) == "video_incompatible" else 503, service.ERRORS.get(str(exc), service.ERRORS["processing_failed"])) from exc
    except StorageError as exc:
        raise HTTPException(413 if "size" in str(exc).lower() else 400, "The video could not be stored within the configured upload limit.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "The video could not be opened or secured.") from exc
    finally:
        await video.close()


@router.get("/jobs")
def listing(current_user: User = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    return {"jobs": [service.public_job(db, job, storage) for job in repository.list_jobs(db, scoped_owner(current_user))]}


@router.get("/jobs/{job_id}")
def detail(job_id: str, current_user: User = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    return {"job": service.public_job(db, owned(job_id, scoped_owner(current_user), db, storage), storage)}


@router.get("/jobs/{job_id}/visualization")
def visualization(
    job_id: str,
    current_user: User = Depends(account),
    db: Session = Depends(get_session),
) -> CleanupFileResponse:
    """Stream only the encrypted privacy-safe review visualization."""

    storage = VideoStorage()
    job = owned(job_id, scoped_owner(current_user), db, storage)
    expected_path = storage.visualization_path(job_id)
    if (
        job.status != "ready"
        or not job.visualization_path
        or Path(job.visualization_path) != expected_path
    ):
        raise HTTPException(409, "The privacy-safe visualization is not available.")
    try:
        materialized = storage.materialize_artifact(
            job_id,
            expected_path,
            f"protected-visualization-{secrets.token_hex(8)}.mp4",
        )
    except StorageError as exc:
        raise HTTPException(409, "The privacy-safe visualization is unavailable.") from exc
    return CleanupFileResponse(
        materialized,
        cleanup=lambda: storage.delete_work_file(materialized),
        media_type="video/mp4",
        filename="protected-video-review.mp4",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store, private", "Pragma": "no-cache", "Vary": "Cookie, Origin"},
    )


@router.get("/jobs/{job_id}/predictions")
def predictions(job_id: str, current_user: User = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    job = owned(job_id, scoped_owner(current_user), db, storage)
    if job.status != "ready" or not job.predictions_path:
        raise HTTPException(409, "Detection results are not available.")
    path = None
    try:
        path = storage.materialize_artifact(job_id, Path(job.predictions_path), f"scores-{secrets.token_hex(16)}.json")
        return json.loads(path.read_text())
    except Exception as exc:
        raise HTTPException(409, "Detection results are unavailable.") from exc
    finally:
        if path:
            storage.delete_work_file(path)
