"""Disposable Docker E2E fixture. No model predictions or patient media are used."""

from datetime import timedelta
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from sqlmodel import Session, select

from backend.app.database.db import engine
from backend.app.database.models.auth import User
from backend.app.database.models.video import utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_detection.contract import validate_predictions


def seed(email: str) -> str:
    if os.environ.get("APP_ENV") != "test":
        raise RuntimeError("Synthetic fixture requires APP_ENV=test")
    with Session(engine) as db:
        user = db.exec(select(User).where(User.email == email)).one()
        job = VideoDetectionJob(owner_user_id=user.id, job_id="VID-" + secrets.token_hex(16).upper(), status="ready", current_stage="complete", duration_seconds=4, fps=30, retention_expires_at=utc_now() + timedelta(minutes=5))
        storage = VideoStorage()
        video = storage.work_path(job.job_id, "synthetic.mp4")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=4", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], check=True)
        job.video_path = str(storage.store_artifact(job.job_id, video, "review.mp4"))
        output = storage.work_path(job.job_id, "predictions.json")
        metadata = {"model_name": "Synthetic test fixture", "model_version": "fixture-only", "weights_hash": "none", "preprocessing_version": "fixture-only", "threshold": 0.5, "sample_fps": 15, "window_frames": 30, "stride_frames": 15, "calibrated": False}
        output.write_text(json.dumps(validate_predictions([{"start_time": 0, "end_time": 2, "raw_score": 0.2}, {"start_time": 1, "end_time": 3, "raw_score": 0.8}], 4, metadata)))
        job.predictions_path = str(storage.store_artifact(job.job_id, output, "predictions.json"))
        db.add(job); db.commit()
        return job.job_id


if __name__ == "__main__":
    print(seed(sys.argv[1]))
