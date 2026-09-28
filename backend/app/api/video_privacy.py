"""Protected endpoints for the standalone video privacy workflow."""

from __future__ import annotations

import hashlib
import re
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.app.core.security import mutation_owner_id, owner_id, require_api_auth
from backend.app.core.config import MAX_VIDEO_UPLOAD_BYTES
from backend.app.core.stream_upload import (
    RequestBodyTooLarge,
    RequestStreamUpload,
    UnsupportedRawUpload,
    request_video_upload,
)
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.api.upload_contracts import video_binary_upload_openapi
from backend.app.database.models.video import VideoPrivacyJob, VideoPrivacyProfile, VideoPrivacyStatus
from backend.app.database.repository import get_video_job, get_video_job_by_idempotency_hash, list_video_jobs
from backend.app.services.storage_service import StorageError
from backend.app.services.video_privacy_service import (
    VideoPrivacyCapacityError,
    VideoPrivacyIdempotencyReplay,
    acknowledge_video_job,
    create_video_job,
    get_download_artifact,
    parse_profile,
    process_video_privacy_job,
    public_video_job,
)
from backend.app.services.video_storage_service import CleanupFileResponse, VideoStorage
from backend.app.video_privacy.processor import VideoProcessorError


router = APIRouter(prefix="/api/video-privacy", tags=["video-privacy"])


async def _drain_upload(upload: RequestStreamUpload) -> None:
    """Consume bounded raw bytes on idempotent replays without storing them."""

    total = 0
    while chunk := await upload.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_VIDEO_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Request body exceeds the configured upload limit.",
            )


async def _replay_video_job(
    db: Session,
    storage: VideoStorage,
    upload: RequestStreamUpload,
    job: VideoPrivacyJob,
    *,
    case_id: str | None,
    profile: VideoPrivacyProfile,
) -> dict:
    """Return the matching owner's job and reject key reuse across intents."""

    await _drain_upload(upload)
    if job.case_id != case_id or job.profile != profile:
        raise HTTPException(status_code=409, detail="The idempotency key belongs to a different video request.")
    if job.status == VideoPrivacyStatus.QUEUED and not job.original_path:
        raise HTTPException(status_code=409, detail="The original request is still being secured. Retry shortly.")
    if (
        upload.content_fingerprint is None
        or job.content_fingerprint is None
        or upload.content_fingerprint != job.content_fingerprint
    ):
        raise HTTPException(status_code=409, detail="The idempotency key belongs to a different video request.")
    return {"job": public_video_job(db, job, storage)}


def _require_authenticated_user(current_user: User | None) -> User:
    """Reject the legacy ownerless development-auth mode for private video."""

    if not isinstance(current_user, User) or current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.post(
    "/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    openapi_extra=video_binary_upload_openapi(profile_required=True),
)
async def create_job(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Encrypt and queue one supported video privacy transform."""

    authenticated_user = _require_authenticated_user(current_user)
    owner_user_id = authenticated_user.id
    if owner_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    profile = request.headers.get("x-video-profile", "")
    case_id = request.headers.get("x-case-id") or None
    raw_idempotency_key = request.headers.get("idempotency-key")
    idempotency_key_hash = None
    if raw_idempotency_key is not None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{16,64}", raw_idempotency_key):
            raise HTTPException(status_code=400, detail="The idempotency key is invalid.")
        idempotency_key_hash = hashlib.sha256(raw_idempotency_key.encode("ascii")).hexdigest()
    try:
        selected_profile = parse_profile(profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        video = request_video_upload(request)
    except UnsupportedRawUpload as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    storage = VideoStorage()
    try:
        if idempotency_key_hash is not None:
            existing = get_video_job_by_idempotency_hash(db, owner_user_id, idempotency_key_hash)
            if existing is not None:
                return await _replay_video_job(
                    db,
                    storage,
                    video,
                    existing,
                    case_id=case_id,
                    profile=selected_profile,
                )
        job = await create_video_job(
            db,
            storage,
            video,
            selected_profile,
            owner_user_id=owner_user_id,
            case_id=case_id,
            idempotency_key_hash=idempotency_key_hash,
        )
    except RequestBodyTooLarge:
        raise
    except VideoPrivacyIdempotencyReplay as replay:
        return await _replay_video_job(
            db,
            storage,
            video,
            replay.job,
            case_id=case_id,
            profile=selected_profile,
        )
    except IntegrityError as exc:
        db.rollback()
        existing = (
            get_video_job_by_idempotency_hash(db, owner_user_id, idempotency_key_hash)
            if idempotency_key_hash is not None
            else None
        )
        if existing is None:
            raise HTTPException(status_code=503, detail="The video could not be secured for processing.") from exc
        return await _replay_video_job(
            db,
            storage,
            video,
            existing,
            case_id=case_id,
            profile=selected_profile,
        )
    except VideoPrivacyCapacityError as exc:
        existing = (
            get_video_job_by_idempotency_hash(db, owner_user_id, idempotency_key_hash)
            if idempotency_key_hash is not None
            else None
        )
        if existing is not None:
            return await _replay_video_job(
                db,
                storage,
                video,
                existing,
                case_id=case_id,
                profile=selected_profile,
            )
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "60"}) from exc
    except HTTPException:
        raise
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
    finally:
        await video.close()
    background_tasks.add_task(process_video_privacy_job, job.job_id)
    return {"job": public_video_job(db, job)}


@router.get("/jobs")
def list_jobs(
    case_id: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """List video privacy jobs without private media metadata."""

    _require_authenticated_user(current_user)
    storage = VideoStorage()
    jobs = list_video_jobs(db, owner_id(current_user), case_id)
    return {"jobs": [public_video_job(db, job, storage) for job in jobs]}


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
