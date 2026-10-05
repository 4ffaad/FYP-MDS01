"""Encrypted video detection jobs and bounded local subprocess execution."""

import asyncio
from datetime import timedelta, timezone
import json
import logging
import math
import os
from pathlib import Path
import secrets
import tempfile
import time
from uuid import UUID
# The runtime passes fixed module arguments and server-generated paths only.
import subprocess  # nosec B404
import sys
import threading

from fastapi import UploadFile
from sqlalchemy import inspect
from sqlmodel import Session

from backend.app.core.config import (
    STORAGE_KEY_ENV,
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_PREFLIGHT_TIMEOUT_SECONDS,
    VIDEO_POSE_READINESS_TIMEOUT_SECONDS,
    VIDEO_RETENTION_SECONDS,
    VSVIG_ALLOW_LETTERBOX_ADAPTATION,
)
from backend.app.database.db import engine
from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.models.video import VideoPrivacyProfile, utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.eeg.legacy_nicolet import video_sync_name_token
from backend.app.privacy.crypto import read_base64_key
from backend.app.database import video_detection_repository as repository
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.video_sync_service import decrypt_sync_payload
from backend.app.services.storage_service import StorageError
from backend.app.services.case_service import (
    cleanup_case_profile_if_empty,
    ensure_case_reference,
    lock_owner_case_mutations,
    new_case_id,
)
from backend.app.video_detection.contract import (
    DEFAULT_PATCH_LABELS,
    DEFAULT_PREPROCESSING,
    DetectionError,
    load_contract,
)
from backend.app.video_detection.visualization import validate_visualization_artifact
from backend.app.video_privacy.processor import (
    MODEL_INPUT_BLUR_MAX_PERCENT,
    MODEL_INPUT_BLUR_MIN_PERCENT,
    VideoPrivacyProcessor,
    VideoProcessorError,
    preflight_video_subprocess,
    video_worker_environment,
)

ERRORS = {
    "assets_missing": "Mount the official model assets by running the pinned VSViG installer; see docs/video-detection.md.",
    "contract_unreviewed": "The VSViG source/runtime contract is not approved or its manifest hash is missing.",
    "contract_invalid": "The VSViG model contract is incomplete or incompatible.",
    "asset_mismatch": "A pinned VSViG, pose, source, or partition asset failed its integrity check.",
    "runtime_incompatible": "The VSViG runtime could not load both published checkpoints. Run the documented runtime verification command.",
    "video_incompatible": "Use a readable AVI, MP4, MOV, or WebM clip of at least 5 seconds with stable frame timing.",
    "video_resolution_mismatch": "This clip does not use the required original 1920×1080 resolution. Select the matching 1920×1080 original, or ask the operator to enable experimental letterboxing.",
    "ambiguous_or_missing_pose": "The pose stage did not find exactly one trackable person in at least one sampled frame. Use footage with one clearly visible person; no VSViG score was produced.",
    "incomplete_pose": "At least one sampled frame lacked a confident, in-frame body landmark required by VSViG. Try clearer lighting and framing; no VSViG score was produced.",
    "pose_readiness_person_count": "The opening five-second pose check could not track exactly one person in every sampled frame. Keep one person clearly visible; no VSViG score was produced.",
    "pose_readiness_landmarks": "The opening five-second pose check missed one or more of VSViG's 15 required landmarks, from the face through the ankles. Improve full-body framing and lighting; no score was produced.",
    "pose_readiness_unavailable": "The pose readiness check could not complete safely. No video score was produced; check the local model runtime and retry.",
    "invalid_patch": "The clip could not produce valid model input patches.",
    "invalid_model_output": "The model returned invalid scores. No detection result was published.",
    "visualization_failed": "The privacy-safe review video could not be generated. No detection result was published.",
    "no_usable_windows": "The clip is too short for a complete model window.",
    "truncated_video": "The video could not be decoded completely.",
    "privacy_transform_failed": "The video could not be face-blurred safely. No detection result was published.",
    "processing_failed": "Video processing failed. Try a shorter supported clip or check the local runtime.",
    "interrupted": "Processing was interrupted by a server restart. Submit the video again.",
    "invalid_blur_strength": "Model-input blur strength must be between 50 and 100 percent.",
    "sync_metadata_invalid": "Video synchronization metadata is invalid.",
}
LOGGER = logging.getLogger(__name__)
# ponytail: one CPU video job at a time per backend process; use a durable worker
# queue before running multiple backend workers or processing hospital batches.
PROCESS_LOCK = threading.Lock()
UPLOAD_LOCK = asyncio.Lock()


def expired(job) -> bool:
    value = job.retention_expires_at
    normalized = (
        value.astimezone(timezone.utc)
        if value.tzinfo is not None
        else value.replace(tzinfo=timezone.utc)
    )
    return normalized <= utc_now()


def _preflight_uploaded_video(
    storage: VideoStorage, job_id: str, encrypted: Path
) -> dict[str, object]:
    """Decrypt once, check metadata, then inspect one model window for pose."""

    deadline = time.monotonic() + VIDEO_PREFLIGHT_TIMEOUT_SECONDS
    source = storage.materialize_original(job_id, encrypted, deadline=deadline)
    try:
        info = preflight_video_subprocess(
            source,
            timeout_seconds=deadline - time.monotonic(),
        )
        if not _video_metadata_admission(info)["accepted"]:
            return info
        return {**info, "pose_readiness": _run_pose_readiness(source)}
    finally:
        storage.delete_work_file(source)


def _video_metadata_admission(info: dict[str, object]) -> dict[str, object]:
    """Describe native metadata admission or enabled experimental adaptation."""

    width = int(info["width"])
    height = int(info["height"])
    fps = float(info["fps"])
    frame_count = int(info["frame_count"])
    duration = frame_count / fps if fps > 0 else 0.0
    needs_adaptation = (width, height) != (1920, 1080)
    if needs_adaptation and not VSVIG_ALLOW_LETTERBOX_ADAPTATION:
        return {
            "accepted": False,
            "width": width,
            "height": height,
            "required_width": 1920,
            "required_height": 1080,
            "adaptation": "none",
            "experimental": False,
            "message": ERRORS["video_resolution_mismatch"],
        }
    if not math.isfinite(duration) or duration < 5 or duration > VIDEO_MAX_DURATION_SECONDS:
        return {
            "accepted": False,
            "width": width,
            "height": height,
            "required_width": 1920,
            "required_height": 1080,
            "adaptation": "letterbox" if needs_adaptation else "none",
            "experimental": needs_adaptation,
            "message": ERRORS["video_incompatible"],
        }
    return {
        "accepted": True,
        "width": width,
        "height": height,
        "required_width": 1920,
        "required_height": 1080,
        "adaptation": "letterbox" if needs_adaptation else "none",
        "experimental": needs_adaptation,
        "fps": fps,
        "duration_seconds": duration,
        "message": (
            "Experimental letterbox adaptation passed preflight. This input has not been validated as equivalent to native-resolution video; results are research-only."
            if needs_adaptation
            else "Native-resolution preflight passed. EEG/video synchronization is not established."
        ),
    }


def _run_pose_readiness(source: Path) -> dict[str, object]:
    """Run pinned OpenPose on one window without loading or calling VSViG."""

    descriptor, result_name = tempfile.mkstemp(
        prefix=".pose-readiness-", suffix=".json", dir=source.parent
    )
    os.close(descriptor)
    result_path = Path(result_name)
    result_path.unlink()
    try:
        execute(
            [
                sys.executable,
                "-m",
                "backend.app.video_detection.runtime",
                "--pose-readiness",
                str(source),
                str(result_path),
                "1" if VSVIG_ALLOW_LETTERBOX_ADAPTATION else "0",
            ],
            VIDEO_POSE_READINESS_TIMEOUT_SECONDS,
        )
        if (
            result_path.is_symlink()
            or not result_path.is_file()
            or result_path.stat().st_size > 16 * 1024
        ):
            raise ValueError("invalid pose readiness result")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid pose readiness result")

        required_frames = DEFAULT_PREPROCESSING["frames"]
        count_fields = (
            "checked_frames",
            "frames_without_person",
            "frames_with_multiple_people",
            "frames_with_tracking_break",
            "frames_with_incomplete_pose",
        )
        if (
            type(payload.get("ready")) is not bool
            or type(payload.get("required_frames")) is not int
            or payload["required_frames"] != required_frames
            or any(
                type(payload.get(field)) is not int
                or not 0 <= payload[field] <= required_frames
                for field in count_fields
            )
            or not isinstance(payload.get("missing_landmarks"), dict)
        ):
            raise ValueError("invalid pose readiness result")
        missing = payload["missing_landmarks"]
        if (
            len(missing) > len(DEFAULT_PATCH_LABELS)
            or any(
                label not in DEFAULT_PATCH_LABELS
                or type(count) is not int
                or not 1 <= count <= required_frames
                for label, count in missing.items()
            )
        ):
            raise ValueError("invalid pose readiness result")
        ready = (
            payload["checked_frames"] == required_frames
            and not any(payload[field] for field in count_fields[1:])
            and not missing
        )
        if payload["ready"] != ready:
            raise ValueError("inconsistent pose readiness result")
        return {
            "ready": ready,
            "checked_frames": payload["checked_frames"],
            "required_frames": required_frames,
            "window_seconds": required_frames / DEFAULT_PREPROCESSING["sample_fps"],
            **{field: payload[field] for field in count_fields[1:]},
            "missing_landmarks": missing,
        }
    except DetectionError:
        raise
    except Exception as exc:
        raise DetectionError("pose_readiness_unavailable") from exc
    finally:
        result_path.unlink(missing_ok=True)


def _pose_readiness_error_code(readiness: object) -> str | None:
    """Return a fixed public reason code, failing closed on malformed results."""

    if not isinstance(readiness, dict) or type(readiness.get("ready")) is not bool:
        return "pose_readiness_unavailable"
    if readiness["ready"]:
        return None
    if any(
        readiness.get(field, 0)
        for field in (
            "frames_without_person",
            "frames_with_multiple_people",
            "frames_with_tracking_break",
        )
    ):
        return "pose_readiness_person_count"
    if readiness.get("frames_with_incomplete_pose") or readiness.get(
        "missing_landmarks"
    ):
        return "pose_readiness_landmarks"
    return "video_incompatible"


def detection_error_detail(error: DetectionError) -> str:
    """Add bounded pose counts to a fixed admission message."""

    code = str(error)
    message = ERRORS.get(code, ERRORS["processing_failed"])
    readiness = error.details.get("pose_readiness")
    if not isinstance(readiness, dict):
        return message

    checked = readiness.get("checked_frames")
    required = readiness.get("required_frames")
    if (
        type(checked) is not int
        or type(required) is not int
        or not 0 <= checked <= DEFAULT_PREPROCESSING["frames"]
        or required != DEFAULT_PREPROCESSING["frames"]
    ):
        return message
    summary = f" Pose check: {checked}/{required} sampled frames checked."
    if code == "pose_readiness_person_count":
        counts = (
            ("no person", readiness.get("frames_without_person")),
            ("multiple people", readiness.get("frames_with_multiple_people")),
            ("tracking breaks", readiness.get("frames_with_tracking_break")),
        )
        counts_text = ", ".join(
            f"{label}: {count}"
            for label, count in counts
            if type(count) is int and 0 <= count <= required
        )
        return message + summary + (f" {counts_text}." if counts_text else "")
    if code == "pose_readiness_landmarks":
        missing = readiness.get("missing_landmarks")
        if not isinstance(missing, dict):
            return message + summary
        labels_text = ", ".join(
            f"{label}: {count}"
            for label in DEFAULT_PATCH_LABELS
            if (count := missing.get(label)) is not None
            and type(count) is int
            and 0 < count <= required
        )
        return message + summary + (
            f" Missing landmark samples: {labels_text}." if labels_text else ""
        )
    return message


def _video_admission(info: dict[str, object]) -> dict[str, object]:
    """Require both valid metadata and a ready opening pose window."""

    admission = _video_metadata_admission(info)
    if not admission["accepted"]:
        return admission
    readiness = info.get("pose_readiness")
    error_code = _pose_readiness_error_code(readiness)
    admission["pose_readiness"] = readiness
    if error_code:
        admission["accepted"] = False
        admission["message"] = ERRORS[error_code]
        return admission
    admission["message"] = (
        "Pose readiness passed for the first five-second model window. "
        "The complete clip is checked again during inference; EEG/video synchronization is not established."
        if admission["adaptation"] == "none"
        else "Experimental letterbox adaptation and pose readiness passed for the first five-second model window. "
        "Later frames are checked again during inference; adapted inputs are not validated as native equivalents."
    )
    return admission


async def preflight_video_upload(storage: VideoStorage, upload: UploadFile) -> dict[str, object]:
    """Encrypt, preflight, and delete one clip without creating an inference job."""

    try:
        storage.cleanup_stale_preflight_uploads()
    except Exception:
        LOGGER.warning("Stale video preflight cleanup unavailable; retrying next sweep.")
    if Path(upload.filename or "").suffix.lower() not in {".avi", ".mp4", ".mov", ".webm"}:
        raise DetectionError("video_incompatible")
    if upload.content_type not in {
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-msvideo",
        "application/octet-stream",
    }:
        raise DetectionError("video_incompatible")
    preflight_id = f"VID-PREFLIGHT-{secrets.token_hex(12).upper()}"
    try:
        with storage.preflight_upload_lease(preflight_id):
            try:
                encrypted = await storage.save_upload(preflight_id, upload)
                info = await asyncio.to_thread(
                    _preflight_uploaded_video, storage, preflight_id, encrypted
                )
                return _video_admission(info)
            except VideoProcessorError:
                return {
                    "accepted": False,
                    "width": None,
                    "height": None,
                    "required_width": 1920,
                    "required_height": 1080,
                    "adaptation": "none",
                    "experimental": False,
                    "message": ERRORS["video_incompatible"],
                }
            finally:
                try:
                    storage.delete_job(preflight_id)
                except Exception as exc:
                    LOGGER.warning("Temporary video preflight cleanup is pending.")
                    raise StorageError("Temporary video cleanup is pending.") from exc
    finally:
        await upload.close()


def _rollback_admission_job(db: Session, job: VideoDetectionJob, storage: VideoStorage) -> bool:
    """Remove an admission job, or persist a terminal retryable failure."""

    job_id = job.job_id
    original_path = job.original_path
    case_id = job.case_id
    owner_user_id = job.owner_user_id
    try:
        storage.delete_job(job_id)
    except Exception:
        LOGGER.warning("Video admission cleanup failed; retaining a terminal retry record.")
        db.rollback()
        job.status = "failed"
        job.current_stage = "cleanup"
        job.error_code = "processing_failed"
        job.original_path = original_path
        db.add(job)
        db.commit()
        return False
    db.delete(job)
    db.commit()
    if case_id and owner_user_id is not None:
        cleanup_case_profile_if_empty(
            db,
            case_id=case_id,
            owner_user_id=owner_user_id,
        )
    return True


def _record_admission_failure(
    db: Session,
    storage: VideoStorage,
    job: VideoDetectionJob,
    error_code: str,
    info: dict[str, object] | None = None,
) -> VideoDetectionJob:
    """Queue a redacted review copy for readable clips rejected by model admission."""

    job.error_code = error_code
    keep_for_review = False
    if info:
        fps = info.get("fps")
        frame_count = info.get("frame_count")
        width = info.get("width")
        height = info.get("height")
        if isinstance(fps, (int, float)) and not isinstance(fps, bool) and fps > 0:
            job.fps = float(fps)
            if (
                isinstance(frame_count, int)
                and not isinstance(frame_count, bool)
                and frame_count > 0
            ):
                job.duration_seconds = frame_count / job.fps
                keep_for_review = (
                    isinstance(width, int)
                    and not isinstance(width, bool)
                    and width > 0
                    and isinstance(height, int)
                    and not isinstance(height, bool)
                    and height > 0
                    and math.isfinite(job.duration_seconds)
                    and job.duration_seconds <= VIDEO_MAX_DURATION_SECONDS
                )
    if keep_for_review:
        job.status = "processing"
        job.current_stage = "privacy-review"
    else:
        try:
            storage.delete_job(job.job_id)
        except Exception:
            _rollback_admission_job(db, job, storage)
            return job
        job.original_path = None
        job.status = "failed"
        job.current_stage = (
            "pose_readiness" if error_code.startswith("pose_readiness") else "preflight"
        )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _make_private_review_copy(
    db: Session,
    storage: VideoStorage,
    job: VideoDetectionJob,
    *,
    processor: VideoPrivacyProcessor | None = None,
) -> bool:
    """Retain an encrypted, audio-free review video after model rejection/failure."""

    source: Path | None = None
    try:
        if expired(job) or not job.original_path:
            expire_job(db, job, storage, force=True)
            return False
        source = storage.materialize_original(job.job_id, Path(job.original_path))
        visual = storage.work_path(job.job_id, "privacy-review.mp4")
        preview = storage.work_path(job.job_id, "privacy-review.jpg")
        output = storage.work_path(job.job_id, "privacy-review-h264.mp4")
        result = (processor or VideoPrivacyProcessor()).process(
            source,
            visual,
            preview,
            VideoPrivacyProfile.FACE_REDACTED,
            allow_full_blur_fallback=True,
        )
        if not result.usable:
            raise VideoProcessorError("Privacy review copy did not meet its safety gate.")
        from backend.app.services.video_privacy_service import finalize_protected_video

        finalize_protected_video(source, visual, output)
        validate_visualization_artifact(
            output,
            expected_fps=result.fps,
            expected_width=result.width,
            expected_height=result.height,
            expected_frame_count=result.frame_count,
            expected_duration=result.duration_seconds,
        )
        job.visualization_path = str(
            storage.store_artifact(job.job_id, output, "video.visualization.mp4")
        )
        storage.cleanup(job.job_id, keep_retained=True)
        job.original_path = None
        job.fps = result.fps
        job.duration_seconds = result.duration_seconds
        job.status = "failed"
        job.current_stage = "privacy-review-ready"
        db.add(job)
        db.commit()
        return True
    except Exception as exc:
        LOGGER.warning(
            "Rejected video review copy failed safely; exception_type=%s",
            type(exc).__name__,
        )
        cleanup_succeeded = True
        try:
            storage.delete_job(job.job_id)
        except Exception:
            cleanup_succeeded = False
            LOGGER.warning("Rejected video review cleanup is pending.")
        job.status = "failed"
        job.current_stage = "privacy-review-failed"
        job.visualization_path = None
        if cleanup_succeeded:
            job.original_path = None
        db.add(job)
        db.commit()
        return False


def process_rejected_review_job(job_id: str) -> None:
    """Build a review-only privacy copy without running OpenPose or VSViG."""

    with PROCESS_LOCK, Session(engine) as db:
        job = repository.get_job(db, job_id, None)
        if (
            job is None
            or job.status != "processing"
            or job.current_stage != "privacy-review"
        ):
            return
        _make_private_review_copy(db, VideoStorage(), job)


def expire_job(db, job, storage, *, force: bool = False):
    if expired(job) and (force or job.status not in {"processing", "validating"}):
        cleanup_succeeded = True
        try:
            storage.delete_job(job.job_id)
        except Exception:
            cleanup_succeeded = False
            LOGGER.warning("Expired video cleanup unavailable; retrying next sweep.")
        job.status = "expired"
        job.current_stage = "expired"
        if cleanup_succeeded:
            job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
        db.add(job)
        db.commit()
    return job


def public_job(db, job, storage):
    expire_job(db, job, storage)
    sync = {
        "status": job.eeg_sync_status,
        "record_id": None,
        "session_id": None,
        "eeg_source_start_seconds": None,
        "video_duration_seconds": None,
        "eeg_coverage_seconds": None,
        "mapped_segments": [],
    }
    if job.eeg_sync_status == "linked" and job.eeg_recording_db_id is not None:
        recording = db.get(EEGRecording, job.eeg_recording_db_id)
        session = db.get(EEGSession, recording.session_db_id) if recording else None
        if (
            recording is not None
            and session is not None
            and session.owner_user_id == job.owner_user_id
            and session.case_id == job.case_id
            and recording.record_id
            and session.session_id
            and session.case_id
        ):
            mapping = decrypt_sync_payload(
                "video-job",
                job.owner_user_id,
                session.case_id,
                job.job_id,
                job.eeg_sync_nonce,
                job.eeg_sync_ciphertext,
            )
            if isinstance(mapping, dict):
                sync.update(
                    {
                        "record_id": recording.record_id,
                        "session_id": session.session_id,
                        "eeg_source_start_seconds": mapping.get(
                            "eeg_source_start_seconds"
                        ),
                        "video_duration_seconds": mapping.get(
                            "video_duration_seconds"
                        ),
                        "eeg_coverage_seconds": mapping.get(
                            "eeg_coverage_seconds"
                        ),
                        "mapped_segments": mapping.get("mapped_segments", []),
                    }
                )
            else:
                sync["status"] = "unavailable"
        else:
            sync["status"] = "unavailable"
    return {
        "job_id": job.job_id, "case_id": job.case_id,
        "label": "Video detection " + job.job_id[-6:],
        "status": job.status, "current_stage": job.current_stage,
        "review_privacy_method": job.review_privacy_method,
        "duration_seconds": job.duration_seconds, "fps": job.fps,
        "blur_strength_percent": job.blur_strength_percent,
        "created_at": job.created_at, "retention_expires_at": job.retention_expires_at,
        "video_available": job.status in {"ready", "failed"}
        and bool(job.visualization_path),
        "error": ERRORS.get(job.error_code), "research_only": True,
        "sync": sync,
    }


def validate_blur_strength_percent(value: object) -> int:
    """Validate the caller-selected percentage before accepting video bytes."""

    if (
        type(value) is not int
        or not MODEL_INPUT_BLUR_MIN_PERCENT <= value <= MODEL_INPUT_BLUR_MAX_PERCENT
    ):
        raise DetectionError("invalid_blur_strength")
    return value


async def create_job(
    db: Session,
    storage: VideoStorage,
    upload: UploadFile,
    owner: int,
    case_id: str | None = None,
    blur_strength_percent: int = MODEL_INPUT_BLUR_MAX_PERCENT,
    source_video_name: str | None = None,
    source_group_id: str | None = None,
):
    validate_blur_strength_percent(blur_strength_percent)
    if Path(upload.filename or "").suffix.lower() not in {".avi", ".mp4", ".mov", ".webm"}:
        raise DetectionError("video_incompatible")
    if upload.content_type not in {
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-msvideo",
        "application/octet-stream",
    }:
        raise DetectionError("video_incompatible")
    source_name_token = None
    if source_video_name is not None or source_group_id is not None:
        try:
            if (
                source_video_name is None
                or source_group_id is None
                or case_id is None
                or not source_video_name
                or len(source_video_name) > 255
                or "/" in source_video_name
                or "\\" in source_video_name
                or Path(source_video_name).suffix.lower()
                not in {".avi", ".mp4", ".mov", ".webm"}
                or str(UUID(source_group_id)) != source_group_id.lower()
            ):
                raise ValueError
            source_name_token = video_sync_name_token(
                source_video_name,
                read_base64_key(STORAGE_KEY_ENV),
                context=f"{owner}:{case_id}",
            )
        except (TypeError, ValueError) as exc:
            raise DetectionError("sync_metadata_invalid") from exc
    ensure_case_reference(db, case_id, owner)
    # Verify the expensive assets off the event loop, before accepting patient bytes.
    await asyncio.to_thread(load_contract)
    if case_id is not None:
        lock_owner_case_mutations(db, owner)
        ensure_case_reference(db, case_id, owner)
    job = VideoDetectionJob(owner_user_id=owner, case_id=case_id or new_case_id(), job_id=f"VID-{secrets.token_hex(16).upper()}",
                            review_privacy_method="tracked-face-blur-with-full-frame-fallback",
                            source_name_token=source_name_token,
                            source_group_id=source_group_id,
                            eeg_sync_status=("pending" if source_group_id else "unavailable"),
                            blur_strength_percent=blur_strength_percent,
                            retention_expires_at=utc_now() + timedelta(seconds=VIDEO_RETENTION_SECONDS))
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        encrypted = await storage.save_upload(job.job_id, upload)
        job.original_path = str(encrypted)
        try:
            info = await asyncio.to_thread(
                _preflight_uploaded_video, storage, job.job_id, encrypted
            )
        except VideoProcessorError:
            return _record_admission_failure(
                db, storage, job, "video_incompatible"
            )
        admission = _video_admission(info)
        if not admission["accepted"]:
            metadata_admission = _video_metadata_admission(info)
            if metadata_admission["accepted"]:
                error_code = _pose_readiness_error_code(info.get("pose_readiness"))
            elif (
                info.get("width") is not None
                and info.get("height") is not None
                and (int(info["width"]), int(info["height"])) != (1920, 1080)
                and not VSVIG_ALLOW_LETTERBOX_ADAPTATION
            ):
                error_code = "video_resolution_mismatch"
            else:
                error_code = "video_incompatible"
            return _record_admission_failure(
                db, storage, job, error_code or "video_incompatible", info
            )
        job.fps = float(info["fps"])
        job.duration_seconds = int(info["frame_count"]) / job.fps
        if not math.isfinite(job.duration_seconds) or not 0 < job.duration_seconds <= VIDEO_MAX_DURATION_SECONDS:
            raise DetectionError("video_incompatible")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except asyncio.CancelledError:
        _rollback_admission_job(db, job, storage)
        raise
    except Exception:
        _rollback_admission_job(db, job, storage)
        raise
    finally:
        await upload.close()


def execute(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=max(1, timeout),
        check=True,
        env=video_worker_environment(),
    )


def process_job(_trigger_job_id: str):
    with PROCESS_LOCK, Session(engine) as db:
        # Each accepted upload schedules this function. Select the oldest
        # accepted row after taking the single-worker lock, so queued work is
        # processed in database order even when request callbacks race.
        job = repository.get_next_queued_job(db)
        if job is None:
            return
        job_id = job.job_id
        storage = VideoStorage()
        if expired(job):
            expire_job(db, job, storage)
            return
        source: Path | None = None
        try:
            job.status, job.current_stage = "processing", "normalization"
            db.add(job)
            db.commit()
            source = storage.materialize_original(job_id, Path(job.original_path))
            source_metadata = VideoPrivacyProcessor.preflight(source)
            source_width = int(source_metadata["width"])
            source_height = int(source_metadata["height"])
            if (source_width, source_height) == (
                DEFAULT_PREPROCESSING["width"],
                DEFAULT_PREPROCESSING["height"],
            ):
                model_input = source
                normalization = {
                    **source_metadata,
                    "source_width": source_width,
                    "source_height": source_height,
                    "adaptation": "none",
                    "source_timestamp_offset_seconds": 0.0,
                    "pad_x": 0,
                    "pad_y": 0,
                    "padding_ltrb": [0, 0, 0, 0],
                }
            else:
                model_input = storage.work_path(job_id, "normalized-input.mp4")
                normalization = VideoPrivacyProcessor.normalize_for_vsvig(
                    source,
                    model_input,
                    allow_letterbox_adaptation=VSVIG_ALLOW_LETTERBOX_ADAPTATION,
                )
            job.duration_seconds = float(normalization["frame_count"]) / float(
                normalization["fps"]
            )
            job.fps = float(normalization["fps"])
            db.add(job)
            db.commit()
            job.current_stage = "pose-and-inference"
            db.add(job)
            db.commit()
            output = storage.work_path(job_id, "predictions.json")
            visualization = storage.work_path(job_id, "privacy-safe-review.mp4")
            expires_at = job.retention_expires_at
            normalized_expiry = (
                expires_at.astimezone(timezone.utc)
                if expires_at.tzinfo is not None
                else expires_at.replace(tzinfo=timezone.utc)
            )
            remaining = lambda: min(3600, (normalized_expiry - utc_now()).total_seconds())
            execute(
                [
                    sys.executable,
                    "-m",
                    "backend.app.video_detection.runtime",
                    str(model_input),
                    str(output),
                    str(visualization),
                    str(model_input),
                    str(job.blur_strength_percent),
                ],
                remaining(),
            )
            result = json.loads(output.read_text())
            visualization_meta = result.get("visualization")
            runtime_duration = result.get("duration_seconds")
            runtime_fps = result.get("fps")
            runtime_frame_count = result.get("frame_count")
            if (
                not isinstance(runtime_duration, (int, float))
                or isinstance(runtime_duration, bool)
                or not math.isfinite(float(runtime_duration))
                or not isinstance(runtime_fps, (int, float))
                or isinstance(runtime_fps, bool)
                or not math.isfinite(float(runtime_fps))
                or type(runtime_frame_count) is not int
                or runtime_frame_count != normalization["frame_count"]
                or not math.isclose(float(runtime_duration), job.duration_seconds, rel_tol=0.0, abs_tol=max(0.1, 1 / max(job.fps, 1)))
                or not math.isclose(float(runtime_fps), job.fps, rel_tol=0.01, abs_tol=0.01)
            ):
                raise DetectionError("invalid_model_output")
            if (
                not result.get("predictions")
                or not isinstance(visualization_meta, dict)
                or visualization_meta.get("available") is not True
                or visualization_meta.get("media_type") != "video/mp4"
                or visualization_meta.get("audio_included") is not False
                or visualization_meta.get("privacy_method") != "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay"
                or not isinstance(visualization_meta.get("overlay"), dict)
                or visualization_meta["overlay"].get("skeleton") is not True
                or not isinstance(visualization_meta.get("quality_flags"), list)
                or type(visualization_meta.get("full_frame_fallback_frames")) is not int
            ):
                raise DetectionError("visualization_failed")
            try:
                visual_frame_count = visualization_meta.get("frame_count")
                visual_fps = visualization_meta.get("fps")
                visual_width = visualization_meta.get("width")
                visual_height = visualization_meta.get("height")
                visual_duration = visualization_meta.get("duration_seconds")
                face_blur_coverage = visualization_meta.get("face_blur_coverage")
                metadata_matches = (
                    type(visual_frame_count) is int
                    and visual_frame_count == normalization["frame_count"]
                    and isinstance(visual_fps, (int, float))
                    and math.isclose(float(visual_fps), job.fps, rel_tol=0.01, abs_tol=0.01)
                    and visual_width == normalization["width"]
                    and visual_height == normalization["height"]
                    and isinstance(visual_duration, (int, float))
                    and abs(float(visual_duration) - job.duration_seconds)
                    <= max(0.1, 1 / max(job.fps, 1))
                    and isinstance(face_blur_coverage, (int, float))
                    and not isinstance(face_blur_coverage, bool)
                    and 0 <= face_blur_coverage <= 1
                    and 0 <= visualization_meta["full_frame_fallback_frames"] <= normalization["frame_count"]
                    and all(isinstance(flag, str) for flag in visualization_meta["quality_flags"])
                )
            except (TypeError, ValueError):
                metadata_matches = False
            if not metadata_matches:
                raise DetectionError("visualization_failed")
            validate_visualization_artifact(
                visualization,
                expected_fps=job.fps,
                expected_width=normalization["width"],
                expected_height=normalization["height"],
                expected_frame_count=normalization["frame_count"],
                expected_duration=job.duration_seconds,
            )
            result["privacy"] = {
                "method": "tracked-face-blur-with-full-frame-fallback",
                "model_input": "15 individually blurred RGB patches per sampled frame",
                "blur_strength_percent": job.blur_strength_percent,
                "pose_model_input": "transient unblurred model frames; only pose coordinates and individually blurred RGB patches reach VSViG",
                "model_input_adaptation": normalization["adaptation"],
                "adaptation_experimental": normalization["adaptation"] == "letterbox",
                "source_resolution": [normalization["source_width"], normalization["source_height"]],
                "model_resolution": [normalization["width"], normalization["height"]],
                "model_input_padding_ltrb": normalization["padding_ltrb"],
                "face_blur_coverage": visualization_meta["face_blur_coverage"],
                "quality_flags": visualization_meta["quality_flags"],
                "review_required": bool(visualization_meta["quality_flags"]),
                "audio_policy": "audio is excluded; only the face-blurred, audio-free review video and encrypted predictions are retained until expiry",
            }
            output.write_text(json.dumps(result, allow_nan=False))
            if expired(job):
                expire_job(db, job, storage, force=True)
                return
            job.predictions_path = str(storage.store_artifact(job_id, output, "predictions.json"))
            job.review_privacy_method = visualization_meta["privacy_method"].removesuffix("-and-skeleton-overlay")
            job.visualization_path = str(
                storage.store_artifact(job_id, visualization, "video.visualization.mp4")
            )
            storage.cleanup(job_id, keep_retained=True)
            job.original_path = None
            job.video_path = None
            job.status, job.current_stage = "ready", "complete"
        except asyncio.CancelledError:
            db.rollback()
            cleanup_succeeded = True
            try:
                storage.delete_job(job_id)
            except Exception:
                cleanup_succeeded = False
                LOGGER.warning("Cancelled video cleanup unavailable; retrying next sweep.")
            job.status = "failed"
            job.current_stage = job.current_stage or "failed"
            job.error_code = "interrupted"
            if cleanup_succeeded:
                job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
            db.add(job)
            db.commit()
            raise
        except Exception as exc:
            LOGGER.warning(
                "Video detection failed at stage=%s exception_type=%s",
                job.current_stage,
                type(exc).__name__,
            )
            db.rollback()
            code = str(exc) if isinstance(exc, DetectionError) else "processing_failed"
            if isinstance(exc, subprocess.CalledProcessError):
                candidate = (exc.stderr or b"").decode(errors="replace").strip()
                if candidate in ERRORS:
                    code = candidate
            review_available = False
            if (
                source is not None
                and source.is_file()
                and code != "privacy_transform_failed"
            ):
                review_available = _make_private_review_copy(
                    db, storage, job, processor=VideoPrivacyProcessor()
                )
            cleanup_succeeded = review_available
            if not review_available:
                cleanup_succeeded = True
                try:
                    storage.delete_job(job_id)
                except Exception:
                    cleanup_succeeded = False
                    LOGGER.warning("Failed video cleanup unavailable; retrying next sweep.")
            if cleanup_succeeded:
                job.original_path = job.video_path = job.predictions_path = None
                if not review_available:
                    job.visualization_path = None
            job.status = "failed"
            if not review_available:
                job.current_stage = job.current_stage or "failed"
            job.error_code = code if code in ERRORS else "processing_failed"
        db.add(job)
        db.commit()


def sweep(*, startup=False):
    """Remove expired ciphertext and safely retry old standalone preflight cleanup."""

    storage = VideoStorage()
    try:
        storage.cleanup_stale_preflight_uploads()
    except Exception:
        LOGGER.warning("Stale video preflight cleanup unavailable; retrying next sweep.")
    if not inspect(engine).has_table(VideoDetectionJob.__tablename__):
        return
    with Session(engine) as db:
        if not startup:
            for ready_job in repository.list_ready_jobs(db):
                try:
                    storage.cleanup_stale_playback(ready_job.job_id)
                    storage.cleanup(
                        ready_job.job_id,
                        keep_retained=True,
                        preserve_playback=True,
                    )
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Ready video work cleanup unavailable; retrying next sweep."
                    )
        jobs = repository.list_all_jobs_for_cleanup(db)
        for job in jobs:
            if job.status == "expired":
                try:
                    storage.delete_job(job.job_id)
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Expired video cleanup unavailable; retrying next sweep."
                    )
                continue
            if job.status == "failed":
                if expired(job):
                    expire_job(db, job, storage, force=True)
                    continue
                if job.visualization_path:
                    try:
                        storage.cleanup_stale_playback(job.job_id)
                        storage.cleanup(
                            job.job_id,
                            keep_retained=True,
                            preserve_playback=True,
                        )
                    except Exception:
                        LOGGER.warning("Failed-job review cleanup is pending.")
                    continue
                cleanup_succeeded = True
                try:
                    storage.delete_job(job.job_id)
                except Exception:
                    cleanup_succeeded = False
                    LOGGER.warning("Failed video cleanup unavailable; retrying next sweep.")
                if cleanup_succeeded:
                    job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
                    db.add(job)
                    db.commit()
                continue
            if startup and job.status in {"queued", "processing"}:
                cleanup_succeeded = True
                try:
                    storage.delete_job(job.job_id)
                except Exception:
                    cleanup_succeeded = False
                    logging.getLogger(__name__).warning(
                        "Interrupted video cleanup unavailable; retrying next sweep."
                    )
                if cleanup_succeeded:
                    job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
                job.status, job.error_code = "failed", "interrupted"
                db.add(job)
                db.commit()
            if startup and job.status == "ready":
                storage.cleanup(job.job_id, keep_retained=True)
            expire_job(db, job, storage)


async def retention_loop():
    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(sweep)
        except Exception:
            # Database availability is reported by health; retry cleanup next tick.
            import logging
            logging.getLogger(__name__).warning("Video retention cleanup unavailable; retrying.")
