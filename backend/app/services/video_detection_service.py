"""Encrypted video detection jobs and bounded local subprocess execution."""

import asyncio
from datetime import timedelta, timezone
import json
import math
from pathlib import Path
import secrets
import subprocess
import sys
import threading

from fastapi import UploadFile
from sqlalchemy import inspect
from sqlmodel import Session

from backend.app.core.config import VIDEO_RETENTION_SECONDS, VIDEO_MAX_DURATION_SECONDS
from backend.app.database.db import engine
from backend.app.database.models.video import VideoPrivacyProfile, utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.database import video_detection_repository as repository
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_detection.contract import DetectionError, load_contract
from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError

ERRORS = {
    "assets_missing": "Mount the official model assets before starting detection.",
    "contract_unreviewed": "The video preprocessing contract needs review before inference can run.",
    "contract_invalid": "The video model contract is incomplete or incompatible.",
    "asset_mismatch": "A video model asset failed its integrity check.",
    "runtime_incompatible": "The video runtime could not load the reviewed model. Check the local setup guide.",
    "video_incompatible": "Use a readable constant-frame-rate MP4, MOV, or WebM within the configured limits.",
    "ambiguous_or_missing_pose": "A single patient could not be identified throughout this clip. Review the framing and try a shorter clip.",
    "incomplete_pose": "Too many patient landmarks were missing or obscured for this model.",
    "invalid_patch": "The clip could not produce valid model input patches.",
    "invalid_model_output": "The model returned invalid scores. No detection result was published.",
    "no_usable_windows": "The clip is too short for a complete model window.",
    "truncated_video": "The video could not be decoded completely.",
    "privacy_transform_failed": "The video could not be face-redacted safely. No detection result was published.",
    "processing_failed": "Video processing failed. Try a shorter supported clip or check the local runtime.",
    "interrupted": "Processing was interrupted by a server restart. Submit the video again.",
}
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


def expire_job(db, job, storage):
    if expired(job):
        storage.delete_job(job.job_id)
        job.status = "expired"
        job.current_stage = "expired"
        job.original_path = job.video_path = job.predictions_path = None
        db.add(job)
        db.commit()
    return job


def public_job(db, job, storage):
    expire_job(db, job, storage)
    return {
        "job_id": job.job_id, "label": "Video detection " + job.job_id[-6:],
        "status": job.status, "current_stage": job.current_stage,
        "duration_seconds": job.duration_seconds, "fps": job.fps,
        "created_at": job.created_at, "retention_expires_at": job.retention_expires_at,
        "video_available": False,
        "error": ERRORS.get(job.error_code), "research_only": True,
    }


async def create_job(db: Session, storage: VideoStorage, upload: UploadFile, owner: int):
    if Path(upload.filename or "").suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise DetectionError("video_incompatible")
    if upload.content_type not in {"video/mp4", "video/quicktime", "video/webm", "application/octet-stream"}:
        raise DetectionError("video_incompatible")
    # Verify the expensive assets off the event loop, before accepting patient bytes.
    await asyncio.to_thread(load_contract)
    job = VideoDetectionJob(owner_user_id=owner, job_id=f"VID-{secrets.token_hex(16).upper()}",
                            retention_expires_at=utc_now() + timedelta(seconds=VIDEO_RETENTION_SECONDS))
    db.add(job)
    db.commit()
    db.refresh(job)
    source = None
    try:
        encrypted = await storage.save_upload(job.job_id, upload)
        job.original_path = str(encrypted)
        source = await asyncio.to_thread(storage.materialize_original, job.job_id, encrypted)
        info = await asyncio.to_thread(VideoPrivacyProcessor.preflight, source)
        job.fps = float(info["fps"])
        job.duration_seconds = int(info["frame_count"]) / job.fps
        if not math.isfinite(job.duration_seconds) or not 0 < job.duration_seconds <= VIDEO_MAX_DURATION_SECONDS:
            raise DetectionError("video_incompatible")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        storage.delete_job(job.job_id)
        db.delete(job)
        db.commit()
        raise
    finally:
        if source:
            source.unlink(missing_ok=True)
        await upload.close()


def execute(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, timeout=max(1, timeout), check=True)


def process_job(job_id: str):
    with PROCESS_LOCK, Session(engine) as db:
        job = repository.get_queued_job(db, job_id)
        if job is None:
            return
        storage = VideoStorage()
        if expired(job):
            expire_job(db, job, storage)
            return
        try:
            job.status, job.current_stage = "processing", "pose-and-inference"
            db.add(job)
            db.commit()
            source = storage.materialize_original(job_id, Path(job.original_path))
            protected_input = storage.work_path(job_id, "model-input.mp4")
            preview = storage.work_path(job_id, "model-input-preview.jpg")
            try:
                privacy = VideoPrivacyProcessor().process(
                    source, protected_input, preview, VideoPrivacyProfile.FACE_REDACTED
                )
            except VideoProcessorError as exc:
                raise DetectionError("privacy_transform_failed") from exc
            if not privacy.usable:
                raise DetectionError("privacy_transform_failed")
            output = storage.work_path(job_id, "predictions.json")
            expires_at = job.retention_expires_at
            normalized_expiry = (
                expires_at.astimezone(timezone.utc)
                if expires_at.tzinfo is not None
                else expires_at.replace(tzinfo=timezone.utc)
            )
            remaining = lambda: min(3600, (normalized_expiry - utc_now()).total_seconds())
            execute([sys.executable, "-m", "backend.app.video_detection.runtime", str(protected_input), str(output)], remaining())
            result = json.loads(output.read_text())
            if not result.get("predictions"):
                raise DetectionError("no_usable_windows")
            result["privacy"] = {
                "method": "face-redaction",
                "model_input": "face-redacted video",
                "face_detection_coverage": privacy.detected_frames / max(privacy.frame_count, 1),
                "quality_flags": privacy.quality_flags,
                "review_required": privacy.needs_review,
            }
            output.write_text(json.dumps(result, allow_nan=False))
            if expired(job):
                expire_job(db, job, storage)
                return
            job.predictions_path = str(storage.store_artifact(job_id, output, "predictions.json"))
            storage.cleanup(job_id, keep_retained=True)
            job.original_path = None
            job.video_path = None
            job.status, job.current_stage = "ready", "complete"
        except Exception as exc:
            code = str(exc) if isinstance(exc, DetectionError) else "processing_failed"
            if isinstance(exc, subprocess.CalledProcessError):
                candidate = (exc.stderr or b"").decode(errors="replace").strip()
                if candidate in ERRORS:
                    code = candidate
            storage.delete_job(job_id)
            job.original_path = job.video_path = job.predictions_path = None
            job.status, job.current_stage = "failed", "failed"
            job.error_code = code if code in ERRORS else "processing_failed"
        db.add(job)
        db.commit()


def sweep(*, startup=False):
    """Remove expired ciphertext without requiring someone to visit the job."""
    if not inspect(engine).has_table(VideoDetectionJob.__tablename__):
        return
    with Session(engine) as db:
        storage = VideoStorage()
        jobs = repository.list_unexpired_jobs(db) if startup else repository.list_expired_jobs(db, utc_now())
        for job in jobs:
            if startup and job.status in {"queued", "processing"}:
                storage.delete_job(job.job_id)
                job.original_path = job.video_path = job.predictions_path = None
                job.status, job.current_stage, job.error_code = "failed", "failed", "interrupted"
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
