"""Privacy and lifecycle tests for the standalone video transform boundary."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import io
import json
import numpy as np
import os
from pathlib import Path
import subprocess
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
    finalize_protected_video,
    parse_profile,
    process_video_privacy_job,
    public_video_job,
)
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_privacy.processor import (
    VideoPrivacyProcessor,
    VideoProcessingResult,
    VideoProcessorError,
    model_frame_layout,
)


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
    def test_model_frame_layout_letterboxes_640x480_without_distortion(self) -> None:
        self.assertEqual(model_frame_layout(640, 480), (1440, 1080, 240, 0))
        self.assertEqual(model_frame_layout(1920, 1080), (1920, 1080, 0, 0))

    def test_vsvig_normalization_rejects_unapproved_resolution_adaptation(self) -> None:
        class Capture:
            def isOpened(self):
                return True

            def release(self):
                return None

        fake_cv2 = type("FakeCV2", (), {"VideoCapture": lambda _path: Capture()})
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"cv2": fake_cv2}), patch.object(
            VideoPrivacyProcessor,
            "_stream_metadata",
            return_value={"fps": 25.0, "width": 640, "height": 480, "frame_count": 10},
        ):
            with self.assertRaisesRegex(VideoProcessorError, "adaptation is not approved"):
                VideoPrivacyProcessor.normalize_for_vsvig(
                    Path(directory) / "source.avi",
                    Path(directory) / "normalized.mp4",
                )

    def test_preflight_rejects_fps_above_the_bounded_video_contract(self) -> None:
        self.preflight_patch.stop()

        class Capture:
            def isOpened(self):
                return True

            def get(self, property_id):
                return {5: 120.0, 3: 1920, 4: 1080, 7: 1200}[property_id]

            def read(self):
                return True, object()

            def release(self):
                return None

        fake_cv2 = type("FakeCV2", (), {
            "CAP_PROP_FPS": 5,
            "CAP_PROP_FRAME_WIDTH": 3,
            "CAP_PROP_FRAME_HEIGHT": 4,
            "CAP_PROP_FRAME_COUNT": 7,
            "VideoCapture": lambda _path: Capture(),
        })
        with patch.dict(sys.modules, {"cv2": fake_cv2}):
            with self.assertRaisesRegex(VideoProcessorError, "frame rate"):
                VideoPrivacyProcessor.preflight(Path("input.mp4"))

    storage_key = b"v" * 32

    def setUp(self) -> None:
        self.preflight_patch = patch(
            "backend.app.services.video_privacy_service.VideoPrivacyProcessor.preflight",
            return_value={"fps": 24.0, "width": 640, "height": 360, "frame_count": 48},
        )
        self.preflight_patch.start()
        self.addCleanup(self.preflight_patch.stop)
        self.finalize_patch = patch(
            "backend.app.services.video_privacy_service.finalize_protected_video",
            side_effect=self._finalize,
        )
        self.finalize_patch.start()
        self.addCleanup(self.finalize_patch.stop)

    @staticmethod
    def _finalize(source: Path, visual: Path, output: Path) -> None:
        output.write_bytes(visual.read_bytes() + b"-private-audio")

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
            self.assertEqual(
                response["profile_description"],
                "The full frame is blurred on every frame. Face-detection coverage is a quality signal for review; it does not change the blur extent.",
            )
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

    def test_api_rejects_pose_only_for_new_jobs_without_echoing_filename(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "test", "AUTH_MODE": "local"}, clear=False):
            with TestClient(app) as client:
                response = client.post(
                    "/api/video-privacy/jobs",
                    data={"profile": "pose-only"},
                    files={"video": ("patient-name.mp4", b"not a video", "video/mp4")},
                )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("patient-name.mp4", response.text)
        self.assertNotIn("original_path", response.text)

    def test_privacy_api_rejects_ownerless_requests_on_every_endpoint(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "test", "AUTH_MODE": "local"}, clear=False):
            with TestClient(app) as client:
                responses = [
                    client.get("/api/video-privacy/jobs"),
                    client.get("/api/video-privacy/jobs/VID-UNKNOWN"),
                    client.post("/api/video-privacy/jobs/VID-UNKNOWN/acknowledge"),
                    client.get("/api/video-privacy/jobs/VID-UNKNOWN/preview"),
                    client.get("/api/video-privacy/jobs/VID-UNKNOWN/download"),
                ]
        self.assertEqual([response.status_code for response in responses], [401] * len(responses))

    def test_face_redaction_is_the_only_new_profile(self) -> None:
        self.assertEqual(parse_profile("face-redacted"), VideoPrivacyProfile.FACE_REDACTED)
        with self.assertRaisesRegex(ValueError, "only available"):
            parse_profile("pose-only")

    def test_legacy_pose_only_transform_fails_closed(self) -> None:
        from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError

        with self.assertRaisesRegex(VideoProcessorError, "Face redaction is the only available"):
            VideoPrivacyProcessor._transform_frame(
                None, None, VideoPrivacyProfile.POSE_ONLY, face_detector=None
            )

    def test_processor_fails_closed_when_cv_runtime_is_missing(self) -> None:
        from backend.app.video_privacy.processor import VideoPrivacyProcessor, VideoProcessorError

        self.preflight_patch.stop()
        with patch.dict(sys.modules, {"cv2": None}):
            with self.assertRaises(VideoProcessorError):
                VideoPrivacyProcessor.preflight(Path("/private/input.mp4"))
        self.preflight_patch.start()

    def test_face_redaction_full_frame_blurs_detected_and_missed_faces(self) -> None:
        from backend.app.video_privacy.processor import VideoPrivacyProcessor

        class Cv:
            COLOR_BGR2GRAY = 1

            @staticmethod
            def cvtColor(frame, _):
                return frame

            @staticmethod
            def GaussianBlur(frame, *_args, **_kwargs):
                return np.full_like(frame, 255)

        frame = np.zeros((4, 4, 3), dtype=np.uint8)

        class FaceDetector:
            @staticmethod
            def detectMultiScale(*_args, **_kwargs):
                return [(0, 0, 2, 2)]

        transformed, detected = VideoPrivacyProcessor._transform_frame(
            Cv, frame, VideoPrivacyProfile.FACE_REDACTED, face_detector=FaceDetector(), pose=None,
        )
        self.assertTrue(detected)
        self.assertEqual(int(transformed[0, 0, 0]), 255)
        self.assertEqual(int(transformed[3, 3, 0]), 255)

        class MissingFace:
            @staticmethod
            def detectMultiScale(*_args, **_kwargs):
                return []

        transformed, detected = VideoPrivacyProcessor._transform_frame(
            Cv, frame, VideoPrivacyProfile.FACE_REDACTED, face_detector=MissingFace(), pose=None,
        )
        self.assertFalse(detected)
        self.assertTrue(np.all(transformed == 255))

        class MultipleFaces:
            @staticmethod
            def detectMultiScale(*_args, **_kwargs):
                return [(0, 0, 2, 2), (2, 2, 2, 2)]

        transformed, detected = VideoPrivacyProcessor._transform_frame(
            Cv, frame, VideoPrivacyProfile.FACE_REDACTED, face_detector=MultipleFaces(), pose=None,
        )
        self.assertFalse(detected)
        self.assertTrue(np.all(transformed == 255))

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
            self.assertNotIn(b"private-audio", (job_root / "retained" / "video.output.mp4.enc").read_bytes())

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

    def test_finalizer_removes_audio_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            visual = Path(directory) / "visual.mp4"
            output = Path(directory) / "protected.mp4"
            source.write_bytes(b"source")
            visual.write_bytes(b"visual")
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                if Path(command[0]).name == "ffmpeg":
                    Path(command[-1]).write_bytes(b"protected")
                    return subprocess.CompletedProcess(command, 0)
                return subprocess.CompletedProcess(
                    command, 0,
                    stdout=json.dumps({"streams": [{"codec_type": "video"}], "format": {}}).encode(),
                )

            self.finalize_patch.stop()
            try:
                with patch("backend.app.services.video_privacy_service.subprocess.run", side_effect=run):
                    finalize_protected_video(source, visual, output)
            finally:
                self.finalize_patch.start()

            ffmpeg = calls[0]
            self.assertIn("-an", ffmpeg)
            self.assertNotIn("1:a:0?", ffmpeg)
            self.assertIn("-map_metadata", ffmpeg)
            self.assertIn("-sn", ffmpeg)
            self.assertIn("-dn", ffmpeg)


if __name__ == "__main__":
    unittest.main()
