"""Application service for the standalone video privacy workflow."""

from __future__ import annotations

import json
import secrets
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session, select

from backend.app.core.config import VIDEO_RETENTION_SECONDS
from backend.app.database.db import engine
from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
    utc_now,
)
from backend.app.database.repository import get_video_job
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError


PROFILE_DETAILS: dict[VideoPrivacyProfile, dict[str, str]] = {
    VideoPrivacyProfile.FACE_REDACTED: {
        "label": "Face redaction",
        "description": "Blur detected faces while keeping the surrounding scene visible.",
    },
    VideoPrivacyProfile.POSE_ONLY: {
        "label": "Pose-only",
        "description": "Replace the scene with pose landmarks on a non-identifying background.",
    },
}


def new_video_job_id() -> str:
    """Create an opaque, non-sequential public job identifier."""

    return f"VID-{secrets.token_hex(16).upper()}"


def parse_profile(value: str | None) -> VideoPrivacyProfile:
    """Parse one of the two approved profile identifiers."""

    try:
        return VideoPrivacyProfile(value or "")
    except ValueError as exc:
        raise ValueError("Choose face-redacted or pose-only.") from exc


def _safe_content_type(upload: UploadFile) -> str:
    """Return a stable output type without retaining client metadata."""

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".webm"}:
        raise ValueError("Upload an MP4, MOV, or WebM video.")
    if upload.content_type and upload.content_type not in {
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "application/octet-stream",
    }:
        raise ValueError("The uploaded stream is not a supported video type.")
    return "video/mp4"


async def create_video_job(
    db: Session,
    storage: VideoStorage,
    upload: UploadFile,
    profile: VideoPrivacyProfile,
) -> VideoPrivacyJob:
    """Create metadata and encrypt the source before queueing processing."""

    content_type = _safe_content_type(upload)
    upload_number = len(list(db.exec(select(VideoPrivacyJob)).all())) + 1
    job = VideoPrivacyJob(
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
        source = storage.materialize_original(job.job_id, encrypted)
        try:
            preflight = VideoPrivacyProcessor.preflight(source)
        finally:
            source.unlink(missing_ok=True)
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
    except Exception:
        storage.delete_job(job.job_id)
        db.delete(job)
        db.commit()
        raise


def _set_stage(db: Session, job: VideoPrivacyJob, stage: str, status: VideoPrivacyStatus) -> None:
    job.current_stage = stage
    job.status = status
    db.add(job)
    db.commit()


def process_video_privacy_job(
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
            output = storage.work_path(job.job_id, "video.output.mp4")
            preview = storage.work_path(job.job_id, "video.preview.jpg")
            result = processor.process(source, output, preview, job.profile)
            _set_stage(db, job, "output-validation", VideoPrivacyStatus.VALIDATING)
            if not result.usable:
                raise VideoProcessorError("Transformed output did not meet the privacy quality threshold.")
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
        except Exception:
            storage.cleanup(job.job_id, keep_retained=False)
            job.status = VideoPrivacyStatus.FAILED
            job.current_stage = job.current_stage or "preflight"
            job.error_message = "The video could not be transformed safely."
            job.original_path = None
            job.output_path = None
            job.preview_path = None
            job.output_usable = False
            db.add(job)
            db.commit()


def _expire_if_needed(db: Session, job: VideoPrivacyJob, storage: VideoStorage | None = None) -> VideoPrivacyJob:
    """Make retention expiry visible without exposing media after expiry."""

    if (
        job.retention_expires_at
        and _is_expired(job.retention_expires_at)
        and job.status not in {VideoPrivacyStatus.FAILED, VideoPrivacyStatus.EXPIRED}
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

    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
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
) -> tuple[VideoPrivacyJob, Path]:
    """Enforce output policy before a route materializes protected media."""

    job = get_video_job(db, job_id)
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
