"""Disposable video-review fixture with encrypted scores and synthetic video."""

from datetime import timedelta
import json
import os
from pathlib import Path
import secrets
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
        if user.id is None:
            raise RuntimeError("Synthetic test account has no database ID")
        job = VideoDetectionJob(
            owner_user_id=user.id,
            job_id="VID-" + secrets.token_hex(16).upper(),
            status="ready",
            current_stage="complete",
            duration_seconds=4,
            fps=30,
            retention_expires_at=utc_now() + timedelta(minutes=5),
        )
        storage = VideoStorage()
        output = storage.work_path(job.job_id, "predictions.json")
        metadata = {
            "model_name": "Synthetic test fixture",
            "model_version": "fixture-only",
            "weights_hash": "none",
            "preprocessing_version": "fixture-only",
            "threshold": 0.5,
            "sample_fps": 15,
            "window_frames": 30,
            "stride_frames": 15,
            "calibrated": False,
        }
        predictions = validate_predictions(
            [
                {"start_time": 0, "end_time": 2, "raw_score": 0.2},
                {"start_time": 1, "end_time": 3, "raw_score": 0.8},
            ],
            4,
            metadata,
        )
        output.write_text(json.dumps(predictions, allow_nan=False))
        job.predictions_path = str(
            storage.store_artifact(job.job_id, output, "predictions.json")
        )
        video = storage.work_path(job.job_id, "synthetic-review.mp4")
        video.write_bytes(
            (Path(__file__).parent / "fixtures" / "synthetic-review.mp4").read_bytes()
        )
        job.visualization_path = str(
            storage.store_artifact(job.job_id, video, "video.visualization.mp4")
        )
        db.add(job)
        db.commit()
        return job.job_id


if __name__ == "__main__":
    print(seed(sys.argv[1]))
