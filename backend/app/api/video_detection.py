"""Authenticated video detection and owner-scoped results."""

import asyncio
import json
import os
from pathlib import Path
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.app.core.security import require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database import video_detection_repository as repository
from backend.app.services import video_detection_service as service
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_detection.contract import DetectionError

router = APIRouter(prefix="/api/video-detection", tags=["video-detection"])


def account(user: User | None = Depends(require_api_auth)) -> int:
    if user is None or user.id is None:
        raise HTTPException(401, "Sign in to use video detection.")
    return user.id


def owned(job_id, owner, db, storage):
    job = repository.get_job(db, job_id, owner)
    if job is None:
        raise HTTPException(404, "Video detection job was not found.")
    return service.expire_job(db, job, storage)


@router.post("/jobs", status_code=202)
async def create(background_tasks: BackgroundTasks, video: UploadFile = File(...),
                 owner: int = Depends(account), db: Session = Depends(get_session)):
    try:
        if os.environ.get("VIDEO_DETECTION_ENABLED", "false").lower() != "true":
            raise HTTPException(503, "Enable the local video detection runtime using the setup guide.")
        async with service.UPLOAD_LOCK:
            if repository.has_active_job(db):
                raise HTTPException(409, "A video is already processing. Try again after it finishes.")
            job = await service.create_job(db, VideoStorage(), video, owner)
        background_tasks.add_task(service.process_job, job.job_id)
        return {"job": service.public_job(db, job, VideoStorage())}
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
def listing(owner: int = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    return {"jobs": [service.public_job(db, job, storage) for job in repository.list_jobs(db, owner)]}


@router.get("/jobs/{job_id}")
def detail(job_id: str, owner: int = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    return {"job": service.public_job(db, owned(job_id, owner, db, storage), storage)}


@router.get("/jobs/{job_id}/predictions")
def predictions(job_id: str, owner: int = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    job = owned(job_id, owner, db, storage)
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
