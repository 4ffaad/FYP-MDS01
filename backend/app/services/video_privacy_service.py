"""Application service for the standalone video privacy workflow."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import shutil
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
)
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError


PROFILE_DETAILS: dict[VideoPrivacyProfile, dict[str, str]] = {
    VideoPrivacyProfile.FACE_REDACTED: {
        "label": "Face redaction",
        "description": "The full frame is blurred on every frame. Face-detection coverage is a quality signal for review; it does not change the blur extent.",
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



def new_video_job_id() -> str:
    """Create an opaque, non-sequential public job identifier."""

    return f"VID-{secrets.token_hex(16).upper()}"


def parse_profile(value: str | None) -> VideoPrivacyProfile:
    """Accept face redaction for new jobs; pose-only remains legacy-readable."""

    if value == VideoPrivacyProfile.FACE_REDACTED.value:
        return VideoPrivacyProfile.FACE_REDACTED
    raise ValueError("Face redaction is the only available privacy transform.")


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
        return VideoPrivacyProcessor.preflight(source, deadline=deadline)
    finally:
        storage.delete_work_file(source)


def _rollback_admission_job(db: Session, job: VideoPrivacyJob, storage: VideoStorage) -> bool:
    """Remove an admission job, or persist a retryable cleanup failure."""

    job_id = job.job_id
    original_path = job.original_path
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
        db.add(job)
        db.commit()
        return False
    db.delete(job)
    db.commit()
    return True


async def create_video_job(
    db: Session,
    storage: VideoStorage,
    upload: UploadFile,
    profile: VideoPrivacyProfile,
    owner_user_id: int | None = None,
) -> VideoPrivacyJob:
    """Create metadata and encrypt the source before queueing processing."""

    content_type = _safe_content_type(upload)
    with VIDEO_PRIVACY_ADMISSION_LOCK:
        if count_active_video_jobs(db) >= VIDEO_PRIVACY_MAX_ACTIVE_JOBS:
            raise VideoPrivacyCapacityError("The video privacy service is at capacity. Try again later.")
        if count_active_video_jobs_for_owner(db, owner_user_id) >= VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER:
            raise VideoPrivacyCapacityError("This account already has a video privacy job in progress.")
        upload_number = count_video_jobs(db, owner_user_id) + 1
        job = VideoPrivacyJob(
            owner_user_id=owner_user_id,
            job_id=new_video_job_id(),
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


def _set_stage(db: Session, job: VideoPrivacyJob, stage: str, status: VideoPrivacyStatus) -> None:
    job.current_stage = stage
    job.status = status
    db.add(job)
    db.commit()


def _mark_privacy_job_failed(
    db: Session,
    job: VideoPrivacyJob,
    storage: VideoStorage,
    *,
    stage: str,
    message: str,
) -> bool:
    """Persist a terminal failure after best-effort private cleanup."""

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
            _set_stage(db, job, "preflight", VideoPrivacyStatus.PREFLIGHT)
            if not job.original_path:
                raise VideoProcessorError("Video source is unavailable.")
            source = storage.materialize_original(job.job_id, Path(job.original_path))
            _set_stage(db, job, "privacy-transform", VideoPrivacyStatus.PROCESSING)
            visual = storage.work_path(job.job_id, "video.visual.mp4")
            output = storage.work_path(job.job_id, "video.output.mp4")
            preview = storage.work_path(job.job_id, "video.preview.jpg")
            result = processor.process(source, visual, preview, job.profile)
            _set_stage(db, job, "output-validation", VideoPrivacyStatus.VALIDATING)
            if not result.usable:
                raise VideoProcessorError("Transformed output did not meet the privacy quality threshold.")
            finalize_protected_video(source, visual, output)
            output_path = storage.store_artifact(job.job_id, output, "video.output.mp4")
            preview_path = storage.store_artifact(job.job_id, preview, "video.preview.jpg")
            job.output_path = str(output_path)
            job.preview_path = str(preview_path)
            job.duration_seconds = result.duration_seconds
            job.fps = result.fps
            job.width = result.width
            job.height = result.height
            job.quality_flags_json = json.dumps(result.quality_flags)
            job.output_usable = result.usable
            job.status = VideoPrivacyStatus.NEEDS_REVIEW if result.needs_review else VideoPrivacyStatus.READY
            job.current_stage = "cleanup"
            job.completed_at = utc_now()
            job.error_message = None
            # Remove encrypted input and all work plaintext before publishing
            # the terminal state to a request that may immediately download.
            storage.cleanup(job.job_id, keep_retained=True)
            job.original_removed_at = utc_now()
            db.add(job)
            db.commit()
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

    active_statuses = ACTIVE_PRIVACY_STATUSES
    if not sqlalchemy_inspect(engine).has_table("video_privacy_jobs"):
        return
    with Session(engine) as db:
        storage = VideoStorage()
        jobs = list(db.exec(select(VideoPrivacyJob)).all())
        for job in jobs:
            if startup and job.status in active_statuses:
                _mark_privacy_job_failed(
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
                _mark_privacy_job_failed(
                    db,
                    job,
                    storage,
                    stage="retention-expired",
                    message="Processing exceeded the private retention window.",
                )
                continue
            if job.status in ACTIVE_PRIVACY_PROCESS_STATUSES:
                continue
            if job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW}:
                try:
                    storage.cleanup(job.job_id, keep_retained=True)
                except Exception:
                    logging.getLogger(__name__).exception("Privacy work cleanup failed")
            elif job.status == VideoPrivacyStatus.FAILED:
                try:
                    storage.cleanup(job.job_id, keep_retained=False)
                except Exception:
                    logging.getLogger(__name__).exception("Failed privacy job cleanup failed")
            _expire_if_needed(db, job, storage)


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
    stage_names = ["preflight", "privacy-transform", "output-validation", "cleanup"]
    completed_index = {
        VideoPrivacyStatus.QUEUED: 0,
        VideoPrivacyStatus.PREFLIGHT: 1,
        VideoPrivacyStatus.PROCESSING: 2,
        VideoPrivacyStatus.VALIDATING: 3,
        VideoPrivacyStatus.READY: 4,
        VideoPrivacyStatus.NEEDS_REVIEW: 4,
        VideoPrivacyStatus.FAILED: 0,
        VideoPrivacyStatus.EXPIRED: 4,
    }[job.status]
    terminal = job.status in {VideoPrivacyStatus.READY, VideoPrivacyStatus.NEEDS_REVIEW, VideoPrivacyStatus.EXPIRED}
    stages = []
    for index, stage in enumerate(stage_names, start=1):
        if terminal:
            stage_status = "complete"
        elif index < completed_index:
            stage_status = "complete"
        elif index == completed_index:
            stage_status = "active"
        else:
            stage_status = "pending"
        stages.append({"id": stage, "status": stage_status})
    return {
        "job_id": job.job_id,
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
