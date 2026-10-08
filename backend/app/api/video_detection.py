"""Authenticated video detection and owner-scoped results."""

import json
import math
import os
from pathlib import Path
import secrets
from collections import Counter
from urllib.parse import unquote_to_bytes
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request

from sqlmodel import Session, select

from backend.app.core.config import STORAGE_KEY_ENV, VIDEO_DETECTION_MAX_QUEUED_JOBS
from backend.app.core.security import owner_id, require_api_auth
from backend.app.core.stream_upload import RequestBodyTooLarge, UnsupportedRawUpload, request_video_upload
from backend.app.eeg.legacy_nicolet import video_sync_name_token
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.api.upload_contracts import video_binary_upload_openapi
from backend.app.database import video_detection_repository as repository
from backend.app.services.case_service import CaseReferenceError, lock_owner_case_mutations
from backend.app.services import video_detection_service as service
from backend.app.services.video_storage_service import VideoStorage
from backend.app.privacy.crypto import read_base64_key
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
    "subjects",
    "recording_probability_available",
    "duration_seconds",
    "fps",
    "frame_count",
    "privacy",
    "visualization",
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
    "blur_strength_percent",
    "pose_model_input",
    "model_input_adaptation",
    "adaptation_experimental",
    "source_resolution",
    "model_resolution",
    "model_input_padding_ltrb",
    "face_detection_coverage",
    "face_blur_coverage",
    "patient_blur_coverage",
    "quality_flags",
    "review_required",
    "audio_policy",
)
_PUBLIC_VISUALIZATION_FIELDS = (
    "available",
    "media_type",
    "audio_included",
    "privacy_method",
    "face_detection_coverage",
    "face_blur_coverage",
    "patient_blur_coverage",
    "full_frame_fallback_frames",
    "quality_flags",
    "frame_count",
    "fps",
    "width",
    "height",
    "duration_seconds",
    "pose_overlay_available",
    "pose_sample_count",
    "overlay",
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
                prediction["model_evidence"],
                (
                    "method",
                    "note",
                    "target_class",
                    "patches",
                    "pose_samples",
                    "gradcam_samples",
                ),
            )
            if "patches" in evidence:
                evidence["patches"] = _allowlisted_rows(
                    evidence["patches"], ("patch_index", "component", "score_change")
                )
            if "pose_samples" in evidence:
                samples = evidence["pose_samples"]
                if not isinstance(samples, list) or len(samples) > 30:
                    raise ValueError("Detection result contains invalid pose samples.")
                safe_samples = []
                for sample in samples:
                    safe_sample = _allowlisted_mapping(sample, ("timestamp", "points"))
                    timestamp = safe_sample.get("timestamp")
                    points = safe_sample.get("points")
                    if (
                        not isinstance(timestamp, (int, float))
                        or isinstance(timestamp, bool)
                        or not math.isfinite(float(timestamp))
                        or not prediction["start_time"] <= timestamp <= prediction["end_time"]
                        or not isinstance(points, list)
                        or len(points) != 15
                    ):
                        raise ValueError("Detection result contains invalid pose samples.")
                    safe_points = _allowlisted_rows(
                        points, ("patch_index", "x", "y", "confidence")
                    )
                    for point in safe_points:
                        if (
                            type(point.get("patch_index")) is not int
                            or not 0 <= point["patch_index"] < 15
                            or any(
                                not isinstance(point.get(field), (int, float))
                                or isinstance(point.get(field), bool)
                                or not math.isfinite(float(point[field]))
                                or not 0 <= point[field] <= 1
                                for field in ("x", "y", "confidence")
                            )
                        ):
                            raise ValueError("Detection result contains invalid pose samples.")
                    if {point["patch_index"] for point in safe_points} != set(range(15)):
                        raise ValueError("Detection result contains invalid pose samples.")
                    safe_sample["points"] = safe_points
                    safe_samples.append(safe_sample)
                evidence["pose_samples"] = safe_samples
            if "gradcam_samples" in evidence:
                samples = evidence["gradcam_samples"]
                if (
                    evidence.get("method") != "vsvig-graph-grad-cam"
                    or evidence.get("target_class") not in {"flagged", "below_threshold"}
                    or not isinstance(samples, list)
                    or len(samples) != 30
                ):
                    raise ValueError("Detection result contains invalid Grad-CAM samples.")
                safe_samples = []
                for sample in samples:
                    safe_sample = _allowlisted_mapping(sample, ("timestamp", "patches"))
                    timestamp = safe_sample.get("timestamp")
                    patches = safe_sample.get("patches")
                    if (
                        not isinstance(timestamp, (int, float))
                        or isinstance(timestamp, bool)
                        or not math.isfinite(float(timestamp))
                        or not prediction["start_time"] <= timestamp <= prediction["end_time"]
                        or not isinstance(patches, list)
                        or len(patches) != 15
                    ):
                        raise ValueError("Detection result contains invalid Grad-CAM samples.")
                    safe_patches = _allowlisted_rows(
                        patches, ("patch_index", "relevance")
                    )
                    for patch in safe_patches:
                        relevance = patch.get("relevance")
                        if (
                            type(patch.get("patch_index")) is not int
                            or not 0 <= patch["patch_index"] < 15
                            or not isinstance(relevance, (int, float))
                            or isinstance(relevance, bool)
                            or not math.isfinite(float(relevance))
                            or not 0 <= relevance <= 1
                        ):
                            raise ValueError("Detection result contains invalid Grad-CAM samples.")
                    if {patch["patch_index"] for patch in safe_patches} != set(range(15)):
                        raise ValueError("Detection result contains invalid Grad-CAM samples.")
                    safe_sample["patches"] = safe_patches
                    safe_samples.append(safe_sample)
                evidence["gradcam_samples"] = safe_samples
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
    if "visualization" in public:
        visualization = _allowlisted_mapping(
            public["visualization"], _PUBLIC_VISUALIZATION_FIELDS
        )
        if "overlay" in visualization:
            visualization["overlay"] = _allowlisted_mapping(
                visualization["overlay"],
                ("skeleton", "model_score", "event_markers"),
            )
        public["visualization"] = visualization
    if "subjects" in public:
        subjects = public["subjects"]
        if not isinstance(subjects, list) or len(subjects) > 100:
            raise ValueError("Detection result contains an invalid track list.")
        safe_subjects = []
        seen_subjects = set()
        for value in subjects:
            subject = _allowlisted_mapping(
                value,
                (
                    "subject_id",
                    "label",
                    "status",
                    "unavailable_reason",
                    "unscored_windows",
                    "predictions",
                    "timeline",
                    "intervals",
                    "events",
                    "summary",
                ),
            )
            subject_id = subject.get("subject_id")
            label = subject.get("label")
            suffix = (
                subject_id.removeprefix("track-")
                if isinstance(subject_id, str)
                else ""
            )
            if (
                not suffix.isdigit()
                or int(suffix) < 1
                or subject_id != f"track-{int(suffix)}"
                or subject_id in seen_subjects
                or label != f"Track {int(suffix)}"
                or subject.get("status") not in {"scored", "unscored"}
            ):
                raise ValueError("Detection result contains an invalid track.")
            seen_subjects.add(subject_id)
            sections = _public_detection_result(
                {
                    "model": model,
                    "predictions": subject.get("predictions"),
                    "timeline": subject.get("timeline", []),
                    "intervals": subject.get("intervals"),
                    "events": subject.get("events", []),
                    **(
                        {"summary": subject["summary"]}
                        if "summary" in subject
                        else {}
                    ),
                    "recording_probability_available": False,
                }
            )
            scored = subject["status"] == "scored"
            if scored != bool(sections["predictions"]):
                raise ValueError("Detection result contains an invalid track status.")
            reason = subject.get("unavailable_reason")
            if (scored and reason is not None) or (
                not scored
                and reason
                not in {"incomplete_pose", "missing_pose", "no_usable_windows"}
            ):
                raise ValueError("Detection result contains an invalid track status.")
            unscored = subject.get("unscored_windows", [])
            if not isinstance(unscored, list) or len(unscored) > 10000:
                raise ValueError("Detection result contains invalid unscored windows.")
            safe_unscored = []
            for window in unscored:
                row = _allowlisted_mapping(
                    window, ("start_time", "end_time", "reason")
                )
                start, end = row.get("start_time"), row.get("end_time")
                if (
                    not isinstance(start, (int, float))
                    or isinstance(start, bool)
                    or not math.isfinite(float(start))
                    or not isinstance(end, (int, float))
                    or isinstance(end, bool)
                    or not math.isfinite(float(end))
                    or not 0 <= start < end <= float(public.get("duration_seconds", end)) + 1e-3
                    or row.get("reason") not in {"incomplete_pose", "missing_pose"}
                ):
                    raise ValueError("Detection result contains invalid unscored windows.")
                safe_unscored.append(row)
            safe_subject = {
                field: sections[field]
                for field in ("predictions", "timeline", "intervals", "events", "summary")
                if field in sections
            }
            safe_subject.update(
                {
                    "subject_id": subject_id,
                    "label": label,
                    "status": subject["status"],
                    "unavailable_reason": reason,
                    "unscored_windows": safe_unscored,
                }
            )
            safe_subjects.append(safe_subject)
        public["subjects"] = safe_subjects
    return public


def account(user: User | None = Depends(require_api_auth)) -> User:
    if user is None or user.id is None:
        raise HTTPException(401, "Sign in to use video detection.")
    return user


def scoped_owner(user: User) -> int | None:
    """Return the shared owner filter for detection reads."""

    return user.id


def owned(job_id, owner, db, storage):
    job = repository.get_job(db, job_id, owner)
    if job is None:
        raise HTTPException(404, "Video detection job was not found.")
    return service.expire_job(db, job, storage)


@router.post(
    "/jobs",
    status_code=202,
    openapi_extra=video_binary_upload_openapi(include_blur_strength=True),
)
async def create(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(account),
    db: Session = Depends(get_session),
):
    case_id = request.headers.get("x-case-id") or None
    reference_only = request.headers.get("x-video-purpose") == "reference"
    try:
        blur_strength_percent = int(
            request.headers.get("x-model-blur-percent", "0")
        )
        if blur_strength_percent != 0:
            raise ValueError("New analyses use unblurred input.")
    except (ValueError, DetectionError) as exc:
        raise HTTPException(422, service.ERRORS["invalid_blur_strength"]) from exc
    source_name_header = request.headers.get("x-veeg-source-name")
    source_group_id = request.headers.get("x-veeg-source-group")
    source_video_name = None
    if source_name_header is not None or source_group_id is not None:
        try:
            if source_name_header is None or source_group_id is None:
                raise ValueError
            source_video_name = unquote_to_bytes(source_name_header).decode("utf-8")
            if len(source_video_name.encode("utf-8")) > 765:
                raise ValueError
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(422, service.ERRORS["sync_metadata_invalid"]) from exc
    owner = current_user.id
    if owner is None:
        raise HTTPException(401, "Sign in to use video detection.")
    try:
        video = request_video_upload(request)
    except UnsupportedRawUpload as exc:
        raise HTTPException(415, str(exc)) from exc
    try:
        if not reference_only and os.environ.get("VIDEO_DETECTION_ENABLED", "false").lower() != "true":
            raise HTTPException(503, "Enable the local video detection runtime using the setup guide.")
        async with service.UPLOAD_LOCK:
            if repository.count_active_jobs(db) >= VIDEO_DETECTION_MAX_QUEUED_JOBS:
                raise HTTPException(
                    429,
                    "The local video queue is full. Wait for a queued clip to finish, then retry this clip.",
                )
            job = (
                await service.create_job(
                    db,
                    VideoStorage(),
                    video,
                    current_user.id,
                    case_id,
                    blur_strength_percent,
                    source_video_name,
                    source_group_id,
                    reference_only=reference_only,
                )
                if case_id
                else await service.create_job(
                    db,
                    VideoStorage(),
                    video,
                    current_user.id,
                    blur_strength_percent=blur_strength_percent,
                    source_video_name=source_video_name,
                    source_group_id=source_group_id,
                    reference_only=reference_only,
                )
            )
        if job.status == "queued":
            background_tasks.add_task(service.process_job, job.job_id)
        elif job.current_stage == "privacy-review":
            background_tasks.add_task(service.process_rejected_review_job, job.job_id)
        return {"job": service.public_job(db, job, VideoStorage())}
    except RequestBodyTooLarge:
        raise
    except CaseReferenceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except DetectionError as exc:
        code = str(exc)
        status = 422 if code in {
            "video_incompatible",
            "video_resolution_mismatch",
            "sync_metadata_invalid",
            "pose_readiness_person_count",
            "pose_readiness_landmarks",
        } else 503
        raise HTTPException(status, service.detection_error_detail(exc)) from exc
    except StorageError as exc:
        raise HTTPException(413 if "size" in str(exc).lower() else 400, "The video could not be stored within the configured upload limit.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "The video could not be opened or secured.") from exc
    finally:
        await video.close()


@router.post("/cases/{case_id}/sync-groups/{group_id}/finalize")
def finalize_video_sync_group(
    case_id: str,
    group_id: str,
    expected_source_names: list[str] = Body(embed=True, min_length=1, max_length=512),
    current_user: User = Depends(account),
    db: Session = Depends(get_session),
):
    """Close one folder upload group and resolve its unique Nicolet mapping."""

    owner = current_user.id
    if owner is None:
        raise HTTPException(401, "Sign in to use video detection.")
    try:
        ensure_group_id = str(UUID(group_id))
        if ensure_group_id != group_id.lower():
            raise ValueError
        from backend.app.services.case_service import ensure_case_reference

        ensure_case_reference(db, case_id, owner)
        lock_owner_case_mutations(db, owner)
    except (ValueError, CaseReferenceError) as exc:
        raise HTTPException(404, "Patient case or synchronization group was not found.") from exc

    group_jobs = list(
        db.exec(
            select(VideoDetectionJob).where(
                VideoDetectionJob.owner_user_id == owner,
                VideoDetectionJob.case_id == case_id,
                VideoDetectionJob.source_group_id == ensure_group_id,
            )
        ).all()
    )
    if not group_jobs:
        db.commit()
        return {"group_id": ensure_group_id, "status": "unmatched", "linked_jobs": 0}
    try:
        if any(
            not isinstance(name, str)
            or not name
            or len(name.encode("utf-8")) > 255
            or "/" in name
            or "\\" in name
            or Path(name).suffix.lower() not in {".avi", ".mp4", ".mov", ".webm"}
            for name in expected_source_names
        ) or sum(len(name.encode("utf-8")) for name in expected_source_names) > 131_072:
            raise ValueError
        expected_tokens = Counter(
            video_sync_name_token(
                name,
                read_base64_key(STORAGE_KEY_ENV),
                context=f"{owner}:{case_id}",
            )
            for name in expected_source_names
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "The video folder manifest is invalid.") from exc
    actual_tokens = Counter(job.source_name_token for job in group_jobs)
    if any(token is None for token in actual_tokens) or actual_tokens != expected_tokens:
        raise HTTPException(
            409,
            "The video folder upload does not match its selected clip manifest. Submit every clip before resolving synchronization.",
        )
    for job in group_jobs:
        job.sync_group_complete = True
        db.add(job)
    from backend.app.services.video_sync_service import resolve_case_video_sync

    linked_jobs = resolve_case_video_sync(
        db, owner, case_id, acquire_lock=False, commit=False
    )
    db.commit()
    refreshed = [db.get(VideoDetectionJob, job.id) for job in group_jobs]
    statuses = {job.eeg_sync_status for job in refreshed if job is not None}
    status = next(iter(statuses)) if len(statuses) == 1 else "ambiguous"
    return {"group_id": ensure_group_id, "status": status, "linked_jobs": linked_jobs}


@router.post("/preflight", openapi_extra=video_binary_upload_openapi())
async def preflight(
    request: Request,
    current_user: User = Depends(account),
):
    """Check clip metadata and opening-window pose readiness without queuing."""

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
        status = 503 if code == "pose_readiness_unavailable" else 422
        raise HTTPException(
            status,
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


@router.get("/jobs/{job_id}/visualization")
def visualization(job_id: str, current_user: User = Depends(account), db: Session = Depends(get_session)):
    storage = VideoStorage()
    job = owned(job_id, scoped_owner(current_user), db, storage)
    if job.status not in {"ready", "failed"} or not job.visualization_path:
        raise HTTPException(409, "The privacy-safe review video is not available.")
    try:
        return storage.visualization_response(job_id, Path(job.visualization_path))
    except Exception as exc:
        raise HTTPException(409, "The privacy-safe review video is unavailable.") from exc


@router.get("/jobs/{job_id}/original")
def original(job_id: str, current_user: User = Depends(account), db: Session = Depends(get_session)):
    from backend.app.services.source_download_service import original_response
    storage = VideoStorage()
    job = owned(job_id, current_user.id, db, storage)
    if not job.original_path:
        raise HTTPException(404, "Original video is unavailable.")
    path = Path(job.original_path)
    if path != storage.root / job.job_id / "original" / "video.input.enc":
        raise HTTPException(404, "Original video is unavailable.")
    try:
        return original_response(storage._storage, job.job_id, path, f"{job.job_id}.video")
    except (StorageError, FileNotFoundError):
        raise HTTPException(404, "Original video is unavailable.")
