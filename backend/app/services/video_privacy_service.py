"""Application service for the standalone video privacy workflow."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
# All subprocess calls below use fixed argv arrays and no shell.
import subprocess  # nosec B404
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlmodel import Session, select

from backend.app.core.config import (
    CLEANUP_INTERVAL_SECONDS,
    VIDEO_MAX_OUTPUT_BYTES,
    VIDEO_PRIVACY_MAX_ACTIVE_JOBS,
    VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER,
    VIDEO_PRIVACY_MAX_CONCURRENT_JOBS,
    VIDEO_PREFLIGHT_TIMEOUT_SECONDS,
    VIDEO_PRIVACY_TIMEOUT_SECONDS,
    VIDEO_RETENTION_SECONDS,
)
from backend.app.database.db import engine
from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
    utc_now,
)
from backend.app.database.repository import (
    count_active_video_jobs,
    count_active_video_jobs_for_owner,
    count_video_jobs,
    get_video_job,
    get_video_job_by_idempotency_hash,
)
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.case_service import (
    cleanup_case_profile_if_empty,
    ensure_case_reference,
    lock_owner_case_mutations,
)
from backend.app.video_privacy.processor import (
    VideoPrivacyProcessor,
    VideoProcessorError,
    preflight_video_subprocess,
)


PROFILE_DETAILS: dict[VideoPrivacyProfile, dict[str, str]] = {
    VideoPrivacyProfile.FACE_REDACTED: {
        "label": "Full-frame blur",
        "description": "The full frame is blurred on every frame. Face-detection coverage is a quality signal for review; it does not change the blur extent.",
    },
    VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW: {
        "label": "Full-frame blur + body-keypoint preview",
        "description": "The full frame is blurred before the pinned Lightweight OpenPose body-joint detector runs. OpenCV renders only a privacy-safe preview; no VSViG score or facial Action Units are produced.",
    },
    VideoPrivacyProfile.POSE_ONLY: {
        "label": "Pose-only",
        "description": "Replace the scene with pose landmarks on a non-identifying background.",
    },
}


LOGGER = logging.getLogger(__name__)
VIDEO_PRIVACY_ADMISSION_LOCK = threading.Lock()
VIDEO_PRIVACY_PROCESS_SEMAPHORE = threading.BoundedSemaphore(VIDEO_PRIVACY_MAX_CONCURRENT_JOBS)
ACTIVE_PRIVACY_PROCESS_STATUSES = frozenset(
    {
        VideoPrivacyStatus.PREFLIGHT,
        VideoPrivacyStatus.PROCESSING,
        VideoPrivacyStatus.VALIDATING,
    }
)
ACTIVE_PRIVACY_STATUSES = ACTIVE_PRIVACY_PROCESS_STATUSES | {VideoPrivacyStatus.QUEUED}


class VideoPrivacyCapacityError(RuntimeError):
    """Raised before upload storage when privacy capacity is exhausted."""


class VideoPrivacyIdempotencyReplay(RuntimeError):
    """Raised when an authenticated owner retries an existing submission."""

    def __init__(self, job: VideoPrivacyJob) -> None:
        super().__init__("This idempotency key already belongs to a video privacy job.")
        self.job = job



def new_video_job_id() -> str:
    """Create an opaque, non-sequential public job identifier."""

    return f"VID-{secrets.token_hex(16).upper()}"


def parse_profile(value: str | None) -> VideoPrivacyProfile:
    """Accept only reviewed face-redaction profiles; legacy pose-only stays disabled."""

    if value == VideoPrivacyProfile.FACE_REDACTED.value:
        return VideoPrivacyProfile.FACE_REDACTED
    if value == VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW.value:
        return VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW
    raise ValueError("Only available profiles are full-frame redaction and redacted pose preview.")


def finalize_protected_video(source: Path, visual: Path, output: Path) -> None:
    """Finalize one audio-free privacy-safe video without source metadata."""

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise VideoProcessorError("Required video tooling is unavailable.")
    success = False
    try:
        if output.is_symlink() or (output.exists() and not output.is_file()):
            raise VideoProcessorError("Protected output path is invalid.")
        output.unlink(missing_ok=True)
        subprocess.run(  # nosec B603
            [
                ffmpeg, "-nostdin", "-v", "error", "-y",
                "-i", str(visual),
                "-map", "0:v:0", "-an", "-c:v", "copy",
                "-map_metadata", "-1", "-map_chapters", "-1", "-sn", "-dn",
                "-movflags", "+faststart", "-fs", str(VIDEO_MAX_OUTPUT_BYTES), str(output),
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=VIDEO_PRIVACY_TIMEOUT_SECONDS,
        )
        if (
            output.is_symlink()
            or not output.is_file()
            or output.stat().st_size == 0
            or output.stat().st_size > VIDEO_MAX_OUTPUT_BYTES
        ):
            raise VideoProcessorError("Protected output exceeded the configured size policy.")
        inspected = subprocess.run(  # nosec B603
            [
                ffprobe, "-v", "error", "-show_entries",
                "format_tags:stream=codec_type:stream_tags", "-of", "json", str(output),
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=VIDEO_PRIVACY_TIMEOUT_SECONDS,
        )
        if len(inspected.stdout) > 64 * 1024:
            raise VideoProcessorError("Protected output metadata exceeded the configured limit.")
        details = json.loads(inspected.stdout)
        streams = details.get("streams", [])
        stream_types = [stream.get("codec_type") for stream in streams]
        format_tags = details.get("format", {}).get("tags", {})
        allowed_format_tags = {"major_brand", "minor_version", "compatible_brands", "encoder"}
        allowed_stream_tags = {"language", "handler_name", "vendor_id"}
        allowed_stream_tag_values = {
            "language": {"und"},
            "handler_name": {"VideoHandler", "SoundHandler"},
            "vendor_id": {"[0][0][0][0]"},
        }
        if (
            stream_types.count("video") != 1
            or stream_types.count("audio") != 0
            or any(kind not in {"video", "audio"} for kind in stream_types)
            or set(format_tags) - allowed_format_tags
            or any(set(stream.get("tags", {})) - allowed_stream_tags for stream in streams)
            or any(
                any(value not in allowed_stream_tag_values[tag] for tag, value in stream.get("tags", {}).items())
                for stream in streams
            )
        ):
            raise VideoProcessorError("Protected output did not meet the audio and metadata policy.")
        success = True
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise VideoProcessorError("Protected output could not be finalized safely.") from exc
    finally:
        if not success:
            try:
                if output.is_symlink() or output.is_file():
                    output.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).exception("Protected output cleanup failed")


def _pose_runtime_environment() -> dict[str, str]:
    """Pass only runtime necessities to the model worker, never API secrets."""

    temp_root = tempfile.gettempdir()
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "PYTHONPATH": os.environ.get(
            "PYTHONPATH", str(Path(__file__).resolve().parents[3])
        ),
        "HOME": temp_root,
        "TMPDIR": temp_root,
        "XDG_CACHE_HOME": os.environ.get(
            "XDG_CACHE_HOME", str(Path(temp_root) / "xdg-cache")
        ),
        "MPLCONFIGDIR": os.environ.get(
            "MPLCONFIGDIR", str(Path(temp_root) / "matplotlib")
        ),
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "NUMEXPR_NUM_THREADS": "2",
    }
    for name in (
        "LD_LIBRARY_PATH",
        "VSVIG_ASSET_DIR",
        "VSVIG_CONTRACT_SHA256",
        "MDS01_NNPACK_ENABLED",
    ):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _run_pose_preview_worker(
    source: Path,
    visualization: Path,
    preview: Path,
    result_path: Path,
    *,
    fps: float,
    width: int,
    height: int,
    frame_count: int,
    duration_seconds: float,
) -> dict[str, int | bool]:
    """Run OpenPose only on the full-frame-blurred intermediate."""

    if source.is_symlink() or not source.is_file():
        raise VideoProcessorError("Blurred pose-preview input is unavailable.")
    outputs = (visualization, preview, result_path)
    for path in outputs:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise VideoProcessorError("Pose-preview output path is invalid.")
        path.unlink(missing_ok=True)

    command = [
        sys.executable,
        "-m",
        "backend.app.video_detection.runtime",
        "--pose-preview",
        str(source),
        str(result_path),
        str(visualization),
        str(preview),
    ]
    try:
        subprocess.run(  # nosec B603
            command,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=VIDEO_PRIVACY_TIMEOUT_SECONDS,
            env=_pose_runtime_environment(),
        )
        if (
            result_path.is_symlink()
            or not result_path.is_file()
            or result_path.stat().st_size > 64 * 1024
        ):
            raise VideoProcessorError("Pose-preview worker returned invalid metadata.")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise VideoProcessorError("The pose preview could not be produced safely.") from exc

    if not isinstance(payload, dict):
        raise VideoProcessorError("Pose-preview metadata is invalid.")
    sampled = payload.get("sampled_frames")
    detected = payload.get("detected_frames")
    tracking_stopped = payload.get("tracking_stopped")
    visual_details = payload.get("visualization")
    if (
        type(sampled) is not int
        or type(detected) is not int
        or not 0 <= detected <= sampled <= frame_count
        or type(tracking_stopped) is not bool
        or not isinstance(visual_details, dict)
        or visual_details.get("available") is not True
        or visual_details.get("audio_included") is not False
        or visual_details.get("pose_sample_count") != detected
        or visual_details.get("pose_overlay_available") is not (detected > 0)
        or visual_details.get("width") != width
        or visual_details.get("height") != height
        or not isinstance(visual_details.get("frame_count"), int)
        or visual_details["frame_count"] != frame_count
        or not isinstance(visual_details.get("fps"), (float, int))
        or abs(float(visual_details["fps"]) - fps) > 0.01
        or not isinstance(visual_details.get("duration_seconds"), (float, int))
        or abs(float(visual_details["duration_seconds"]) - duration_seconds)
        > max(0.1, 1 / max(fps, 1))
        or visualization.is_symlink()
        or not visualization.is_file()
        or preview.is_symlink()
        or not preview.is_file()
        or preview.stat().st_size <= 0
        or preview.stat().st_size > 2 * 1024 * 1024
    ):
        raise VideoProcessorError("Pose-preview output did not meet the safety contract.")

    from backend.app.video_detection.visualization import validate_visualization_artifact

    validate_visualization_artifact(
        visualization,
        expected_fps=fps,
        expected_width=width,
        expected_height=height,
        expected_frame_count=frame_count,
        expected_duration=duration_seconds,
    )
    return {
        "sampled_frames": sampled,
        "detected_frames": detected,
        "tracking_stopped": tracking_stopped,
    }


def _safe_content_type(upload: UploadFile) -> str:
    """Return a stable output type without retaining client metadata."""

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in {".avi", ".mp4", ".mov", ".webm"}:
        raise ValueError("Upload an AVI, MP4, MOV, or WebM video.")
    if upload.content_type and upload.content_type not in {
        "video/x-msvideo",
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "application/octet-stream",
    }:
        raise ValueError("The uploaded stream is not a supported video type.")
    return "video/mp4"


def _preflight_uploaded_video(storage: VideoStorage, job_id: str, encrypted: Path) -> dict[str, float | int]:
    """Decrypt and preflight one upload under a cooperative wall-clock deadline."""

    deadline = time.monotonic() + VIDEO_PREFLIGHT_TIMEOUT_SECONDS
    source = storage.materialize_original(job_id, encrypted, deadline=deadline)
    try:
        return preflight_video_subprocess(
            source,
            timeout_seconds=deadline - time.monotonic(),
        )
    finally:
        storage.delete_work_file(source)


def _rollback_admission_job(db: Session, job: VideoPrivacyJob, storage: VideoStorage) -> bool:
    """Remove an admission job, or persist a retryable cleanup failure."""

    job_id = job.job_id
    original_path = job.original_path
    case_id = job.case_id
    owner_user_id = job.owner_user_id
    content_fingerprint = job.content_fingerprint
    try:
        storage.delete_job(job_id)
    except Exception:
        LOGGER.warning("Privacy admission cleanup failed; retaining a terminal retry record.")
        db.rollback()
        job.status = VideoPrivacyStatus.FAILED
        job.current_stage = "cleanup"
        job.error_message = "The upload could not be secured and cleanup is pending."
        job.output_usable = False
        job.original_path = original_path
        job.content_fingerprint = content_fingerprint
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


async def create_video_job(
    db: Session,
    storage: VideoStorage,
    upload: UploadFile,
    profile: VideoPrivacyProfile,
    owner_user_id: int | None = None,
    case_id: str | None = None,
    idempotency_key_hash: str | None = None,
) -> VideoPrivacyJob:
    """Create metadata and encrypt the source before queueing processing."""

    if case_id is not None:
        lock_owner_case_mutations(db, owner_user_id)
    ensure_case_reference(db, case_id, owner_user_id)
    content_type = _safe_content_type(upload)
    with VIDEO_PRIVACY_ADMISSION_LOCK:
        if idempotency_key_hash is not None and owner_user_id is not None:
            existing = get_video_job_by_idempotency_hash(db, owner_user_id, idempotency_key_hash)
            if existing is not None:
                raise VideoPrivacyIdempotencyReplay(existing)
        if count_active_video_jobs(db) >= VIDEO_PRIVACY_MAX_ACTIVE_JOBS:
            raise VideoPrivacyCapacityError("The video privacy service is at capacity. Try again later.")
        if count_active_video_jobs_for_owner(db, owner_user_id) >= VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER:
            raise VideoPrivacyCapacityError("This account already has a video privacy job in progress.")
        upload_number = count_video_jobs(db, owner_user_id) + 1
        job = VideoPrivacyJob(
            owner_user_id=owner_user_id,
            case_id=case_id,
            job_id=new_video_job_id(),
            idempotency_key_hash=idempotency_key_hash,
            profile=profile,
            display_label=f"Video upload {upload_number:02d}",
            content_type=content_type,
            status=VideoPrivacyStatus.QUEUED,
            current_stage="preflight",
            retention_expires_at=utc_now() + timedelta(seconds=VIDEO_RETENTION_SECONDS),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
    try:
        encrypted = await storage.save_upload(job.job_id, upload)
        fingerprint = getattr(upload, "content_fingerprint", None)
        if idempotency_key_hash is not None:
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                raise ValueError("The uploaded stream could not be fingerprinted completely.")
            job.content_fingerprint = fingerprint
        job.original_path = str(encrypted)
        # Size is a coarse technical field, not client-provided identity.
        job.file_size_bytes = max(0, encrypted.stat().st_size)
        preflight = await asyncio.to_thread(_preflight_uploaded_video, storage, job.job_id, encrypted)
        job.fps = float(preflight["fps"])
        job.width = int(preflight["width"])
        job.height = int(preflight["height"])
        frame_count = int(preflight["frame_count"])
        if job.fps > 0 and frame_count > 0:
            job.duration_seconds = frame_count / job.fps
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


def _privacy_job_lock_statement(job_id: str):
    """Build the durable row mutex shared by workers and retention sweepers."""

    return (
        select(VideoPrivacyJob)
        .where(VideoPrivacyJob.job_id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _lock_privacy_job(db: Session, job_id: str) -> VideoPrivacyJob | None:
    """Lock and refresh the job row before a state or storage transition."""

    return db.exec(_privacy_job_lock_statement(job_id)).first()


def _cleanup_non_active_job(storage: VideoStorage, job_id: str, status: VideoPrivacyStatus | None) -> None:
    """Discard stale worker files without deleting another worker's published result."""

    try:
        if status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}:
            storage.cleanup(job_id, keep_retained=True)
        else:
            storage.delete_job(job_id)
    except Exception:
        LOGGER.warning("Stale privacy worker cleanup is pending.")


def _set_stage(
    db: Session,
    job: VideoPrivacyJob,
    stage: str,
    status: VideoPrivacyStatus,
    storage: VideoStorage,
) -> bool:
    """Advance only a still-active row while holding its database lock."""

    current = _lock_privacy_job(db, job.job_id)
    if current is None or current.status not in ACTIVE_PRIVACY_STATUSES:
        db.rollback()
        _cleanup_non_active_job(storage, job.job_id, current.status if current else None)
        return False
    current.current_stage = stage
    current.status = status
    db.add(current)
    db.commit()
    return True


def _fail_locked_privacy_job(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage,
    *,
    stage: str,
    message: str,
) -> bool:
    """Persist a terminal failure while the caller owns the job row lock."""

    cleanup_succeeded = True
    try:
        storage.cleanup(job.job_id, keep_retained=False)
    except Exception:
        cleanup_succeeded = False
        LOGGER.exception("Privacy job cleanup failed after processing error.")
    job.status = VideoPrivacyStatus.FAILED
    job.current_stage = stage if cleanup_succeeded else "cleanup"
    job.error_message = message
    job.output_usable = False
    if cleanup_succeeded:
        job.original_path = None
        job.output_path = None
        job.preview_path = None
    db.add(job)
    db.commit()
    return cleanup_succeeded


def _mark_privacy_job_failed(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage,
    *,
    stage: str,
    message: str,
) -> bool:
    """Persist failure only if no other worker or sweeper made the row terminal."""

    current = _lock_privacy_job(db, job.job_id)
    if current is None or current.status not in ACTIVE_PRIVACY_STATUSES:
        db.rollback()
        _cleanup_non_active_job(storage, job.job_id, current.status if current else None)
        return False
    return _fail_locked_privacy_job(
        db,
        current,
        storage,
        stage=stage,
        message=message,
    )


def _publish_privacy_result(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage,
    output: Path,
    preview: Path,
    result,
) -> bool:
    """Encrypt and publish outputs under the same PostgreSQL row lock as expiry."""

    current = _lock_privacy_job(db, job.job_id)
    if current is None or current.status not in ACTIVE_PRIVACY_PROCESS_STATUSES:
        db.rollback()
        _cleanup_non_active_job(storage, job.job_id, current.status if current else None)
        return False
    if current.retention_expires_at and _is_expired(current.retention_expires_at):
        _fail_locked_privacy_job(
            db,
            current,
            storage,
            stage="retention-expired",
            message="Processing exceeded the private retention window.",
        )
        return False

    output_path = storage.store_artifact(current.job_id, output, "video.output.mp4")
    preview_path = storage.store_artifact(current.job_id, preview, "video.preview.jpg")
    current.output_path = str(output_path)
    current.preview_path = str(preview_path)
    current.duration_seconds = result.duration_seconds
    current.fps = result.fps
    current.width = result.width
    current.height = result.height
    current.pose_detected_frames = result.pose_detected_frames
    current.pose_sampled_frames = result.pose_sampled_frames
    current.quality_flags_json = json.dumps(result.quality_flags)
    current.output_usable = result.usable
    current.status = VideoPrivacyStatus.NEEDS_REVIEW if result.needs_review else VideoPrivacyStatus.READY
    current.current_stage = "cleanup"
    current.completed_at = utc_now()
    current.error_message = None
    storage.cleanup(current.job_id, keep_retained=True)
    current.original_path = None
    current.original_removed_at = utc_now()

    if current.retention_expires_at and _is_expired(current.retention_expires_at):
        cleanup_succeeded = True
        try:
            storage.delete_job(current.job_id)
        except Exception:
            cleanup_succeeded = False
            LOGGER.warning("Expired privacy publication cleanup is pending.")
        current.status = VideoPrivacyStatus.FAILED
        current.current_stage = "retention-expired" if cleanup_succeeded else "cleanup"
        current.error_message = "Processing exceeded the private retention window."
        current.output_usable = False
        if cleanup_succeeded:
            current.original_path = None
            current.output_path = None
            current.preview_path = None
    db.add(current)
    db.commit()
    return current.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}


def process_video_privacy_job(
    job_id: str,
    *,
    storage: VideoStorage | None = None,
    processor: VideoPrivacyProcessor | None = None,
) -> None:
    """Run one privacy job under the configured global worker limit."""

    VIDEO_PRIVACY_PROCESS_SEMAPHORE.acquire()
    try:
        _process_video_privacy_job(job_id, storage=storage, processor=processor)
    finally:
        VIDEO_PRIVACY_PROCESS_SEMAPHORE.release()


def _process_video_privacy_job(
    job_id: str,
    *,
    storage: VideoStorage | None = None,
    processor: VideoPrivacyProcessor | None = None,
) -> None:
    """Run one queued job in a fresh database session and clean plaintext."""

    storage = storage or VideoStorage()
    processor = processor or VideoPrivacyProcessor()
    with Session(engine) as db:
        job = get_video_job(db, job_id)
        if job is None or job.status not in {VideoPrivacyStatus.QUEUED, VideoPrivacyStatus.PREFLIGHT}:
            return
        source: Path | None = None
        output: Path | None = None
        preview: Path | None = None
        try:
            if not _set_stage(db, job, "preflight", VideoPrivacyStatus.PREFLIGHT, storage):
                return
            if not job.original_path:
                raise VideoProcessorError("Video source is unavailable.")
            source = storage.materialize_original(job.job_id, Path(job.original_path))
            if not _set_stage(db, job, "privacy-transform", VideoPrivacyStatus.PROCESSING, storage):
                return
            visual = storage.work_path(job.job_id, "video.visual.mp4")
            output = storage.work_path(job.job_id, "video.output.mp4")
            preview = storage.work_path(job.job_id, "video.preview.jpg")
            if job.profile == VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW:
                blurred = storage.work_path(job.job_id, "video.blurred.mp4")
                blurred_preview = storage.work_path(
                    job.job_id, "video.blurred-preview.jpg"
                )
                result = processor.process(
                    source,
                    blurred,
                    blurred_preview,
                    VideoPrivacyProfile.FACE_REDACTED,
                    allow_full_blur_fallback=True,
                )
                if not result.usable:
                    raise VideoProcessorError(
                        "Transformed output did not meet the privacy quality threshold."
                    )
                if not _set_stage(
                    db,
                    job,
                    "keypoint-preview",
                    VideoPrivacyStatus.PROCESSING,
                    storage,
                ):
                    return
                pose = _run_pose_preview_worker(
                    blurred,
                    visual,
                    preview,
                    storage.work_path(job.job_id, "pose-preview.json"),
                    fps=result.fps,
                    width=result.width,
                    height=result.height,
                    frame_count=result.frame_count,
                    duration_seconds=result.duration_seconds,
                )
                quality_flags = list(result.quality_flags)
                pose_is_partial = pose["detected_frames"] < pose["sampled_frames"]
                if pose["detected_frames"] == 0:
                    quality_flags.append("pose_keypoints_not_detected")
                elif pose_is_partial:
                    quality_flags.append("pose_keypoints_partial")
                if pose["tracking_stopped"]:
                    quality_flags.append("pose_tracking_stopped")
                result = replace(
                    result,
                    pose_detected_frames=pose["detected_frames"],
                    pose_sampled_frames=pose["sampled_frames"],
                    quality_flags=quality_flags,
                    needs_review=(
                        result.needs_review
                        or pose_is_partial
                        or pose["tracking_stopped"]
                    ),
                )
            else:
                result = processor.process(source, visual, preview, job.profile)
            if not _set_stage(
                db,
                job,
                "output-validation",
                VideoPrivacyStatus.VALIDATING,
                storage,
            ):
                return
            if not result.usable:
                raise VideoProcessorError("Transformed output did not meet the privacy quality threshold.")
            finalize_protected_video(source, visual, output)
            _publish_privacy_result(db, job, storage, output, preview, result)
        except asyncio.CancelledError:
            _mark_privacy_job_failed(
                db,
                job,
                storage,
                stage="interrupted",
                message="Processing stopped before completion.",
            )
            raise
        except Exception:
            _mark_privacy_job_failed(
                db,
                job,
                storage,
                stage=job.current_stage or "preflight",
                message="The video could not be transformed safely.",
            )


def sweep_video_privacy_jobs(*, startup: bool = False) -> None:
    """Clean standalone privacy work and expire retained output safely."""

    if not sqlalchemy_inspect(engine).has_table("video_privacy_jobs"):
        return
    with Session(engine) as db:
        storage = VideoStorage()
        job_ids = list(db.exec(select(VideoPrivacyJob.job_id)).all())
        for job_id in job_ids:
            job = _lock_privacy_job(db, job_id)
            if job is None:
                db.rollback()
                continue
            if startup and job.status in ACTIVE_PRIVACY_STATUSES:
                _fail_locked_privacy_job(
                    db,
                    job,
                    storage,
                    stage="recovered-after-restart",
                    message="Processing stopped before completion.",
                )
                continue
            if (
                job.status in ACTIVE_PRIVACY_PROCESS_STATUSES
                and job.retention_expires_at
                and _is_expired(job.retention_expires_at)
            ):
                _fail_locked_privacy_job(
                    db,
                    job,
                    storage,
                    stage="retention-expired",
                    message="Processing exceeded the private retention window.",
                )
                continue
            if job.status in ACTIVE_PRIVACY_PROCESS_STATUSES:
                db.rollback()
                continue
            if job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}:
                try:
                    storage.cleanup(job.job_id, keep_retained=True)
                except Exception:
                    LOGGER.exception("Privacy work cleanup failed")
            elif job.status in {VideoPrivacyStatus.FAILED, VideoPrivacyStatus.EXPIRED}:
                try:
                    storage.cleanup(job.job_id, keep_retained=False)
                except Exception:
                    LOGGER.exception("Failed privacy job cleanup failed")
            _expire_if_needed(db, job, storage)
            if db.in_transaction():
                db.rollback()


async def video_privacy_retention_loop(interval_seconds: int = CLEANUP_INTERVAL_SECONDS) -> None:
    """Periodically sweep standalone privacy jobs until application shutdown."""

    while True:
        try:
            await asyncio.to_thread(sweep_video_privacy_jobs)
        except Exception:
            logging.getLogger(__name__).exception("Privacy retention sweep failed")
        await asyncio.sleep(interval_seconds)


def _expire_if_needed(db: Session, job: VideoPrivacyJob, storage: VideoStorage | None = None) -> VideoPrivacyJob:
    """Make retention expiry visible without exposing media after expiry."""

    if (
        job.retention_expires_at
        and _is_expired(job.retention_expires_at)
        and job.status not in {
            VideoPrivacyStatus.FAILED,
            VideoPrivacyStatus.EXPIRED,
            *ACTIVE_PRIVACY_PROCESS_STATUSES,
        }
    ):
        if storage is not None:
            storage.delete_job(job.job_id)
        job.status = VideoPrivacyStatus.EXPIRED
        job.current_stage = "retention-expired"
        job.original_path = None
        job.output_path = None
        job.preview_path = None
        job.output_usable = False
        db.add(job)
        db.commit()
    return job


def _is_expired(value) -> bool:
    """Compare SQLite's naive timestamps and PostgreSQL's aware timestamps uniformly."""

    normalized = (
        value.astimezone(timezone.utc)
        if value.tzinfo is not None
        else value.replace(tzinfo=timezone.utc)
    )
    return normalized <= utc_now()


def public_video_job(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage | None = None,
) -> dict[str, Any]:
    """Serialize only generated labels, status, quality, and policy fields."""

    job = _expire_if_needed(db, job, storage)
    details = PROFILE_DETAILS[job.profile]
    is_ready = job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}
    acknowledged = job.acknowledged_at is not None
    download_available = (
        is_ready
        and job.output_usable
        and (job.status == VideoPrivacyStatus.READY or acknowledged)
        and bool(job.retention_expires_at and not _is_expired(job.retention_expires_at))
    )
    stage_names = ["preflight", "privacy-transform"]
    if job.profile == VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW:
        stage_names.append("keypoint-preview")
    stage_names.extend(["output-validation", "cleanup"])
    terminal = job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW, VideoPrivacyStatus.EXPIRED}
    active_index = (
        stage_names.index(job.current_stage)
        if job.current_stage in stage_names
        else -1
    )
    stages = []
    for index, stage in enumerate(stage_names):
        if terminal:
            stage_status = "complete"
        elif index < active_index:
            stage_status = "complete"
        elif index == active_index:
            stage_status = "active"
        else:
            stage_status = "pending"
        stages.append({"id": stage, "status": stage_status})
    pose_evidence = None
    if job.profile == VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW:
        detected = job.pose_detected_frames or 0
        sampled = job.pose_sampled_frames or 0
        pose_evidence = {
            "model": "Lightweight OpenPose",
            "detected_frames": detected,
            "sampled_frames": sampled,
            "tracking_stopped": "pose_tracking_stopped" in job.quality_flags(),
            "status": (
                "not-detected"
                if detected == 0
                else "partial"
                if detected < sampled
                else "complete"
            ),
            "action_units": "not-configured",
        }
    return {
        "job_id": job.job_id,
        "case_id": job.case_id,
        "label": job.display_label,
        "profile": job.profile.value,
        "profile_label": details["label"],
        "profile_description": details["description"],
        "status": job.status.value,
        "current_stage": job.current_stage,
        "stages": stages,
        "quality_flags": job.quality_flags(),
        "output_usable": job.output_usable,
        "requires_acknowledgement": job.status == VideoPrivacyStatus.NEEDS_REVIEW and job.output_usable and not acknowledged,
        "acknowledged": acknowledged,
        "preview_available": is_ready and bool(job.preview_path),
        "preview_url": f"/api/video-privacy/jobs/{job.job_id}/preview" if is_ready and job.preview_path else None,
        "download_available": download_available,
        "download_url": f"/api/video-privacy/jobs/{job.job_id}/download" if download_available else None,
        "retention_expires_at": job.retention_expires_at.isoformat() if job.retention_expires_at else None,
        "duration_seconds": job.duration_seconds,
        "fps": job.fps,
        "width": job.width,
        "height": job.height,
        "pose_evidence": pose_evidence,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error_message,
        "research_only": True,
        "anonymity_not_guaranteed": True,
    }


def acknowledge_video_job(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage | None = None,
) -> VideoPrivacyJob:
    """Record explicit acknowledgement for a usable needs-review output."""

    if job.status != VideoPrivacyStatus.NEEDS_REVIEW or not job.output_usable:
        raise ValueError("This output does not require acknowledgement.")
    if job.retention_expires_at and _is_expired(job.retention_expires_at):
        _expire_if_needed(db, job, storage)
        raise ValueError("This protected output has expired.")
    job.acknowledged_at = utc_now()
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_download_artifact(
    db: Session,
    job_id: str,
    *,
    preview: bool = False,
    storage: VideoStorage | None = None,
    owner_user_id: int | None = None,
) -> tuple[VideoPrivacyJob, Path]:
    """Enforce output policy before a route materializes protected media."""

    job = get_video_job(db, job_id, owner_user_id)
    if job is None:
        raise LookupError("Video job was not found.")
    _expire_if_needed(db, job, storage)
    if preview:
        if job.status not in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW} or not job.preview_path:
            raise PermissionError("A protected preview is not available yet.")
        return job, Path(job.preview_path)
    if not (
        job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}
        and job.output_usable
        and (job.status == VideoPrivacyStatus.READY or job.acknowledged_at)
        and job.output_path
        and job.retention_expires_at
        and not _is_expired(job.retention_expires_at)
    ):
        raise PermissionError("Protected output is not available under the current policy.")
    return job, Path(job.output_path)
