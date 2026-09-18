"""Encrypted video detection jobs and bounded local subprocess execution."""

import asyncio
from datetime import timedelta, timezone
import json
import logging
import math
from pathlib import Path
import secrets
import time
# The runtime passes fixed module arguments and server-generated paths only.
import subprocess  # nosec B404
import sys
import threading

from fastapi import UploadFile
from sqlalchemy import inspect
from sqlmodel import Session

from backend.app.core.config import (
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_PREFLIGHT_TIMEOUT_SECONDS,
    VIDEO_RETENTION_SECONDS,
)
from backend.app.database.db import engine
from backend.app.database.models.video import VideoPrivacyProfile, utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.database import video_detection_repository as repository
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.case_service import ensure_case_reference, new_case_id
from backend.app.video_detection.contract import DetectionError, load_contract
from backend.app.video_detection.visualization import validate_visualization_artifact
from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError

ERRORS = {
    "assets_missing": "Mount the official model assets by running the pinned VSViG installer; see docs/video-detection.md.",
    "contract_unreviewed": "The VSViG source/runtime contract is not approved or its manifest hash is missing.",
    "contract_invalid": "The VSViG model contract is incomplete or incompatible.",
    "asset_mismatch": "A pinned VSViG, pose, source, or partition asset failed its integrity check.",
    "runtime_incompatible": "The VSViG runtime could not load both published checkpoints. Run the documented runtime verification command.",
    "video_incompatible": "Use a readable constant-frame-rate video at 1920x1080 with at least 5 seconds of visual content.",
    "ambiguous_or_missing_pose": "A single patient could not be identified throughout this clip. Review the framing and try a shorter clip.",
    "incomplete_pose": "Too many patient landmarks were missing or obscured for this model.",
    "invalid_patch": "The clip could not produce valid model input patches.",
    "invalid_model_output": "The model returned invalid scores. No detection result was published.",
    "visualization_failed": "The privacy-safe review video could not be generated. No detection result was published.",
    "no_usable_windows": "The clip is too short for a complete model window.",
    "truncated_video": "The video could not be decoded completely.",
    "privacy_transform_failed": "The video could not be face-redacted safely. No detection result was published.",
    "processing_failed": "Video processing failed. Try a shorter supported clip or check the local runtime.",
    "interrupted": "Processing was interrupted by a server restart. Submit the video again.",
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


def _preflight_uploaded_video(storage: VideoStorage, job_id: str, encrypted: Path):
    """Decrypt and preflight one detection upload under one deadline."""

    deadline = time.monotonic() + VIDEO_PREFLIGHT_TIMEOUT_SECONDS
    source = storage.materialize_original(job_id, encrypted, deadline=deadline)
    try:
        return VideoPrivacyProcessor.preflight(source, deadline=deadline)
    finally:
        storage.delete_work_file(source)


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
    visualization_available = job.status == "ready" and bool(job.visualization_path)
    return {
        "job_id": job.job_id, "case_id": job.case_id,
        "label": "Video detection " + job.job_id[-6:],
        "status": job.status, "current_stage": job.current_stage,
        "duration_seconds": job.duration_seconds, "fps": job.fps,
        "created_at": job.created_at, "retention_expires_at": job.retention_expires_at,
        "video_available": False,
        "visualization_available": visualization_available,
        "visualization_url": f"/api/video-detection/jobs/{job.job_id}/visualization" if visualization_available else None,
        "error": ERRORS.get(job.error_code), "research_only": True,
    }


async def create_job(
    db: Session,
    storage: VideoStorage,
    upload: UploadFile,
    owner: int,
    case_id: str | None = None,
):
    if Path(upload.filename or "").suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise DetectionError("video_incompatible")
    if upload.content_type not in {"video/mp4", "video/quicktime", "video/webm", "application/octet-stream"}:
        raise DetectionError("video_incompatible")
    ensure_case_reference(db, case_id, owner)
    # Verify the expensive assets off the event loop, before accepting patient bytes.
    await asyncio.to_thread(load_contract)
    job = VideoDetectionJob(owner_user_id=owner, case_id=case_id or new_case_id(), job_id=f"VID-{secrets.token_hex(16).upper()}",
                            retention_expires_at=utc_now() + timedelta(seconds=VIDEO_RETENTION_SECONDS))
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        encrypted = await storage.save_upload(job.job_id, upload)
        job.original_path = str(encrypted)
        info = await asyncio.to_thread(_preflight_uploaded_video, storage, job.job_id, encrypted)
        job.fps = float(info["fps"])
        job.duration_seconds = int(info["frame_count"]) / job.fps
        if not math.isfinite(job.duration_seconds) or not 0 < job.duration_seconds <= VIDEO_MAX_DURATION_SECONDS:
            raise DetectionError("video_incompatible")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except asyncio.CancelledError:
        storage.delete_job(job.job_id)
        db.delete(job)
        db.commit()
        raise
    except Exception:
        storage.delete_job(job.job_id)
        db.delete(job)
        db.commit()
        raise
    finally:
        await upload.close()


def execute(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,  # nosec B603
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
            job.status, job.current_stage = "processing", "privacy-transform"
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
            job.duration_seconds = privacy.duration_seconds
            job.fps = privacy.fps
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
                    str(protected_input),
                    str(output),
                    str(visualization),
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
                or runtime_frame_count != privacy.frame_count
                or not math.isclose(float(runtime_duration), privacy.duration_seconds, rel_tol=0.0, abs_tol=max(0.1, 1 / max(privacy.fps, 1)))
                or not math.isclose(float(runtime_fps), privacy.fps, rel_tol=0.01, abs_tol=0.01)
            ):
                raise DetectionError("invalid_model_output")
            if (
                not result.get("predictions")
                or not isinstance(visualization_meta, dict)
                or visualization_meta.get("available") is not True
                or visualization_meta.get("media_type") != "video/mp4"
                or visualization_meta.get("audio_included") is not False
                or visualization_meta.get("privacy_method") != "full-frame-blur-and-skeleton-overlay"
                or not isinstance(visualization_meta.get("overlay"), dict)
                or visualization_meta["overlay"].get("skeleton") is not True
            ):
                raise DetectionError("visualization_failed")
            try:
                visual_frame_count = visualization_meta.get("frame_count")
                visual_fps = visualization_meta.get("fps")
                visual_width = visualization_meta.get("width")
                visual_height = visualization_meta.get("height")
                visual_duration = visualization_meta.get("duration_seconds")
                metadata_matches = (
                    type(visual_frame_count) is int
                    and visual_frame_count == privacy.frame_count
                    and isinstance(visual_fps, (int, float))
                    and math.isclose(float(visual_fps), privacy.fps, rel_tol=0.01, abs_tol=0.01)
                    and visual_width == privacy.width
                    and visual_height == privacy.height
                    and isinstance(visual_duration, (int, float))
                    and abs(float(visual_duration) - privacy.duration_seconds)
                    <= max(0.1, 1 / max(privacy.fps, 1))
                )
            except (TypeError, ValueError):
                metadata_matches = False
            if not metadata_matches:
                raise DetectionError("visualization_failed")
            validate_visualization_artifact(
                visualization,
                expected_fps=privacy.fps,
                expected_width=privacy.width,
                expected_height=privacy.height,
                expected_frame_count=privacy.frame_count,
                expected_duration=privacy.duration_seconds,
            )
            result["privacy"] = {
                "method": "face-detection-and-full-frame-blur",
                "model_input": "full-frame-blurred video",
                "face_detection_coverage": privacy.detected_frames / max(privacy.frame_count, 1),
                "quality_flags": privacy.quality_flags,
                "review_required": privacy.needs_review,
                "audio_policy": "audio is excluded from model input and the retained privacy-safe visualization",
                "visualization": {
                    "retained": "encrypted_owner_scoped_preview",
                    "audio_included": False,
                    "method": "full-frame-blur-and-skeleton-overlay",
                },
            }
            output.write_text(json.dumps(result, allow_nan=False))
            if expired(job):
                expire_job(db, job, storage, force=True)
                return
            job.predictions_path = str(storage.store_artifact(job_id, output, "predictions.json"))
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
            job.status, job.current_stage = "failed", "interrupted"
            job.error_code = "interrupted"
            if cleanup_succeeded:
                job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
            db.add(job)
            db.commit()
            raise
        except Exception as exc:
            db.rollback()
            cleanup_succeeded = True
            try:
                storage.delete_job(job_id)
            except Exception:
                cleanup_succeeded = False
                LOGGER.warning("Failed video cleanup unavailable; retrying next sweep.")
            code = str(exc) if isinstance(exc, DetectionError) else "processing_failed"
            if isinstance(exc, subprocess.CalledProcessError):
                candidate = (exc.stderr or b"").decode(errors="replace").strip()
                if candidate in ERRORS:
                    code = candidate
            if cleanup_succeeded:
                job.original_path = job.video_path = job.visualization_path = job.predictions_path = None
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
        if not startup:
            for ready_job in repository.list_ready_jobs(db):
                try:
                    storage.cleanup(ready_job.job_id, keep_retained=True)
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
