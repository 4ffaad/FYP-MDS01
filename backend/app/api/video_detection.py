"""Authenticated video detection and owner-scoped results."""

import json
import os
from pathlib import Path
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from sqlmodel import Session

from backend.app.core.security import owner_id, require_api_auth
from backend.app.core.stream_upload import RequestBodyTooLarge, UnsupportedRawUpload, request_video_upload
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.api.upload_contracts import video_binary_upload_openapi
from backend.app.database import video_detection_repository as repository
from backend.app.services.case_service import CaseReferenceError
from backend.app.services import video_detection_service as service
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_detection.contract import DetectionError

router = APIRouter(prefix="/api/video-detection", tags=["video-detection"])

_PUBLIC_RESULT_FIELDS = (
    "model",
    "predictions",
    "timeline",
    "intervals",
    "events",
    "summary",
    "recording_probability_available",
    "duration_seconds",
    "fps",
    "frame_count",
    "privacy",
)
_PUBLIC_MODEL_FIELDS = (
    "model_name",
    "model_version",
    "weights_hash",
    "preprocessing_version",
    "contract_version",
    "threshold",
    "sample_fps",
    "window_frames",
    "stride_frames",
    "calibrated",
    "pose_model",
    "pose_weights_hash",
    "partition_hash",
    "input_resolution",
    "patch_labels",
    "source_repository",
    "pose_repository",
    "privacy_input",
    "postprocessing",
)
_PUBLIC_WINDOW_FIELDS = (
    "start_time",
    "end_time",
    "raw_score",
    "score",
    "score_type",
    "seizure_detected",
    "threshold",
    "model_evidence",
    *_PUBLIC_MODEL_FIELDS,
)
_PUBLIC_PRIVACY_FIELDS = (
    "method",
    "model_input",
    "pose_model_input",
    "model_input_adaptation",
    "adaptation_experimental",
    "source_resolution",
    "model_resolution",
    "model_input_padding_ltrb",
    "face_detection_coverage",
    "quality_flags",
    "review_required",
    "audio_policy",
)


def _allowlisted_mapping(value: object, fields: tuple[str, ...]) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Detection result contains an invalid object.")
    return {field: value[field] for field in fields if field in value}


def _allowlisted_rows(value: object, fields: tuple[str, ...]) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("Detection result contains an invalid list.")
    return [_allowlisted_mapping(row, fields) for row in value]


def _public_detection_result(payload: object) -> dict:
    """Project decrypted artifacts onto the reviewed public result contract."""

    public = _allowlisted_mapping(payload, _PUBLIC_RESULT_FIELDS)
    required = {"model", "predictions", "intervals", "recording_probability_available"}
    if not required.issubset(public):
        raise ValueError("Detection result is incomplete.")

    model = _allowlisted_mapping(public["model"], _PUBLIC_MODEL_FIELDS)
    if "input_resolution" in model:
        model["input_resolution"] = _allowlisted_mapping(
            model["input_resolution"], ("width", "height")
        )
    public["model"] = model

    public["predictions"] = _allowlisted_rows(
        public["predictions"], _PUBLIC_WINDOW_FIELDS
    )
    for prediction in public["predictions"]:
        if "model_evidence" in prediction:
            evidence = _allowlisted_mapping(
                prediction["model_evidence"], ("method", "note", "patches")
            )
            if "patches" in evidence:
                evidence["patches"] = _allowlisted_rows(
                    evidence["patches"], ("patch_index", "component", "score_change")
                )
            prediction["model_evidence"] = evidence

    public["intervals"] = _allowlisted_rows(
        public["intervals"], ("start_time", "end_time")
    )
    if "timeline" in public:
        public["timeline"] = _allowlisted_rows(
            public["timeline"],
            ("timestamp", "start_time", "end_time", "score", "seizure_detected"),
        )
    if "events" in public:
        public["events"] = _allowlisted_rows(
            public["events"],
            ("start_time", "end_time", "peak_score", "peak_timestamp"),
        )
    if "summary" in public:
        public["summary"] = _allowlisted_mapping(
            public["summary"],
            ("peak_score", "potential_event_detected", "event_count", "threshold"),
        )
    if "privacy" in public:
        public["privacy"] = _allowlisted_mapping(
            public["privacy"], _PUBLIC_PRIVACY_FIELDS
        )
    return public


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


@router.post("/jobs", status_code=202, openapi_extra=video_binary_upload_openapi())
async def create(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(account),
    db: Session = Depends(get_session),
):
    case_id = request.headers.get("x-case-id") or None
    owner = current_user.id
    if owner is None:
        raise HTTPException(401, "Sign in to use video detection.")
    try:
        video = request_video_upload(request)
    except UnsupportedRawUpload as exc:
        raise HTTPException(415, str(exc)) from exc
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
    except RequestBodyTooLarge:
        raise
    except CaseReferenceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except DetectionError as exc:
        code = str(exc)
        status = 422 if code in {"video_incompatible", "video_resolution_mismatch"} else 503
        raise HTTPException(status, service.ERRORS.get(code, service.ERRORS["processing_failed"])) from exc
    except StorageError as exc:
        raise HTTPException(413 if "size" in str(exc).lower() else 400, "The video could not be stored within the configured upload limit.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "The video could not be opened or secured.") from exc
    finally:
        await video.close()


@router.post("/preflight", openapi_extra=video_binary_upload_openapi())
async def preflight(
    request: Request,
    current_user: User = Depends(account),
):
    """Check a clip's native resolution and timing without creating a job."""

    try:
        video = request_video_upload(request)
    except UnsupportedRawUpload as exc:
        raise HTTPException(415, str(exc)) from exc
    try:
        async with service.UPLOAD_LOCK:
            return await service.preflight_video_upload(VideoStorage(), video)
    except RequestBodyTooLarge:
        raise
    except DetectionError as exc:
        code = str(exc)
        raise HTTPException(
            422,
            service.ERRORS.get(code, service.ERRORS["video_incompatible"]),
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            413 if "size" in str(exc).lower() else 503,
            "The temporary video check could not complete safely. Retry or use a supported local clip.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, service.ERRORS["video_incompatible"]) from exc
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


@router.get("/jobs/{job_id}/predictions")
def predictions(job_id: str, current_user: User = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    job = owned(job_id, scoped_owner(current_user), db, storage)
    if job.status != "ready" or not job.predictions_path:
        raise HTTPException(409, "Detection results are not available.")
    path = None
    try:
        path = storage.materialize_artifact(job_id, Path(job.predictions_path), f"scores-{secrets.token_hex(16)}.json")
        return _public_detection_result(json.loads(path.read_text()))
    except Exception as exc:
        raise HTTPException(409, "Detection results are unavailable.") from exc
    finally:
        if path:
            storage.delete_work_file(path)
