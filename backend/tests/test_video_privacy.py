"""Privacy and lifecycle tests for the standalone video transform boundary."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.models.video import VideoPrivacyJob, VideoPrivacyProfile, VideoPrivacyStatus
from backend.app.main import app
from backend.app.services.video_privacy_service import (
    acknowledge_video_job,
    create_video_job,
    process_video_privacy_job,
    public_video_job,
)
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_privacy.processor import VideoProcessingResult


class FakeProcessor:
    """Write deterministic transformed artifacts without optional CV runtimes."""

    def __init__(self, *, needs_review: bool = False) -> None:
        self.needs_review = needs_review

    def process(self, source_path: Path, output_path: Path, preview_path: Path, profile: VideoPrivacyProfile) -> VideoProcessingResult:
        output_path.write_bytes(b"transformed-video-without-audio")
        preview_path.write_bytes(b"transformed-preview-frame")
        return VideoProcessingResult(
            duration_seconds=2.0,
            fps=24.0,
            width=640,
            height=360,
            frame_count=48,
            detected_frames=40,
            quality_flags=["intermittent_detection"] if self.needs_review else [],
            usable=True,
            needs_review=self.needs_review,
        )


class VideoPrivacyTests(unittest.TestCase):
    storage_key = b"v" * 32

    def setUp(self) -> None:
        self.preflight_patch = patch(
            "backend.app.services.video_privacy_service.VideoPrivacyProcessor.preflight",
            return_value={"fps": 24.0, "width": 640, "height": 360, "frame_count": 48},
        )
        self.preflight_patch.start()
        self.addCleanup(self.preflight_patch.stop)

    def _database(self):
        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(database)
        self.addCleanup(database.dispose)
        return database

    def _upload(self, filename: str = "patient.mov") -> UploadFile:
        return UploadFile(filename=filename, file=io.BytesIO(b"encrypted source bytes"), headers={"content-type": "video/quicktime"})

    def test_public_job_has_only_generated_label_and_no_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            storage = VideoStorage(Path(directory) / "sessions", storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(create_video_job(db, storage, self._upload("patient-name.mov"), VideoPrivacyProfile.FACE_REDACTED))
                response = public_video_job(db, job)

            serialized = repr(response)
            self.assertEqual(response["label"], "Video upload 01")
            self.assertNotIn("patient-name.mov", serialized)
            self.assertNotIn("original_path", response)
            self.assertNotIn(str(Path(directory)), serialized)

    def test_video_upload_size_limit_rolls_back_job_and_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            storage = VideoStorage(Path(directory) / "sessions", storage_key=self.storage_key)
            with patch("backend.app.services.video_storage_service.MAX_VIDEO_UPLOAD_BYTES", 2):
                with Session(database) as db:
                    with self.assertRaises(StorageError):
                        asyncio.run(create_video_job(db, storage, self._upload(), VideoPrivacyProfile.FACE_REDACTED))
                    self.assertEqual(db.exec(select(VideoPrivacyJob)).all(), [])
            self.assertEqual(list((Path(directory) / "sessions").iterdir()), [])

    def test_api_rejects_unknown_profile_without_echoing_filename(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/video-privacy/jobs",
                data={"profile": "clinical-action-analysis"},
                files={"video": ("patient-name.mp4", b"not a video", "video/mp4")},
            )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("patient-name.mp4", response.text)
        self.assertNotIn("original_path", response.text)

    def test_processor_fails_closed_when_cv_runtime_is_missing(self) -> None:
        from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError

        self.preflight_patch.stop()
        with patch.dict(sys.modules, {"cv2": None}):
            with self.assertRaises(VideoProcessorError):
                VideoPrivacyProcessor.preflight(Path("/private/input.mp4"))
        self.preflight_patch.start()

    def test_processing_encrypts_outputs_and_removes_plaintext_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            root = Path(directory) / "sessions"
            storage = VideoStorage(root, storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(create_video_job(db, storage, self._upload(), VideoPrivacyProfile.FACE_REDACTED))
                job_id = job.job_id

            with patch("backend.app.services.video_privacy_service.engine", database):
                process_video_privacy_job(job_id, storage=storage, processor=FakeProcessor())

            with Session(database) as db:
                job = db.exec(select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)).one()
                self.assertEqual(job.status, VideoPrivacyStatus.READY)
                self.assertTrue(job.output_usable)
                self.assertEqual(public_video_job(db, job)["profile"], "face-redacted")
            job_root = root / job_id
            self.assertFalse((job_root / "original").exists())
            self.assertFalse((job_root / "work").exists())
            self.assertTrue((job_root / "retained" / "video.output.mp4.enc").exists())
            self.assertTrue((job_root / "retained" / "video.preview.jpg.enc").exists())
            self.assertNotEqual((job_root / "retained" / "video.output.mp4.enc").read_bytes(), b"transformed-video-without-audio")

    def test_needs_review_requires_acknowledgement_before_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            storage = VideoStorage(Path(directory) / "sessions", storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(create_video_job(db, storage, self._upload(), VideoPrivacyProfile.POSE_ONLY))
                job_id = job.job_id
            with patch("backend.app.services.video_privacy_service.engine", database):
                process_video_privacy_job(job_id, storage=storage, processor=FakeProcessor(needs_review=True))
            with Session(database) as db:
                job = db.exec(select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)).one()
                public = public_video_job(db, job)
                self.assertEqual(job.status, VideoPrivacyStatus.NEEDS_REVIEW)
                self.assertTrue(public["requires_acknowledgement"])
                self.assertFalse(public["download_available"])
                acknowledged = acknowledge_video_job(db, job)
                self.assertTrue(public_video_job(db, acknowledged)["download_available"])

    def test_expiry_removes_retained_artifacts_when_job_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            root = Path(directory) / "sessions"
            storage = VideoStorage(root, storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(create_video_job(db, storage, self._upload(), VideoPrivacyProfile.FACE_REDACTED))
                job_id = job.job_id
            with patch("backend.app.services.video_privacy_service.engine", database):
                process_video_privacy_job(job_id, storage=storage, processor=FakeProcessor())
            with Session(database) as db:
                job = db.exec(select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)).one()
                job.retention_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
                db.add(job)
                db.commit()
                public = public_video_job(db, job, storage)
                self.assertEqual(public["status"], "expired")
                self.assertFalse(public["preview_available"])
            self.assertFalse((root / job_id).exists())


if __name__ == "__main__":
    unittest.main()
