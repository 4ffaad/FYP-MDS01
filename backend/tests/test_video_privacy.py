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
import threading
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
    sweep_video_privacy_jobs,
    _pose_runtime_environment,
    _privacy_job_lock_statement,
    _run_pose_preview_worker,
)
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.storage_service import StorageError
from backend.app.video_privacy.processor import (
    VideoPrivacyProcessor,
    VideoProcessingResult,
    VideoProcessorError,
)


class FakeProcessor(VideoPrivacyProcessor):
    """Write deterministic transformed artifacts without optional CV runtimes."""

    def __init__(self, *, needs_review: bool = False) -> None:
        self.needs_review = needs_review

    def process(
        self,
        source_path: Path,
        output_path: Path,
        preview_path: Path,
        profile: VideoPrivacyProfile,
        *,
        allow_full_blur_fallback: bool = False,
    ) -> VideoProcessingResult:
        self.allow_full_blur_fallback = allow_full_blur_fallback
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
    def test_full_blur_pose_preview_can_retain_safe_low_coverage_for_review(self) -> None:
        redaction_flags, redaction_usable, redaction_needs_review = VideoPrivacyProcessor._quality_assessment(
            detected_frames=0,
            frame_count=12,
            allow_full_blur_fallback=False,
        )
        pose_flags, pose_usable, pose_needs_review = VideoPrivacyProcessor._quality_assessment(
            detected_frames=0,
            frame_count=12,
            allow_full_blur_fallback=True,
        )

        self.assertFalse(redaction_usable)
        self.assertFalse(redaction_needs_review)
        self.assertEqual(redaction_flags, ["no_detection"])
        self.assertTrue(pose_usable)
        self.assertTrue(pose_needs_review)
        self.assertEqual(pose_flags, ["no_detection"])

    def test_pose_runtime_environment_does_not_inherit_api_secrets(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MDS01_STORAGE_KEY": "not-a-real-key",
                "DATABASE_URL": "postgresql://not-a-real-connection",
                "VSVIG_ASSET_DIR": "/opt/vsvig",
                "MDS01_NNPACK_ENABLED": "false",
            },
            clear=True,
        ):
            environment = _pose_runtime_environment()

        self.assertNotIn("MDS01_STORAGE_KEY", environment)
        self.assertNotIn("DATABASE_URL", environment)
        self.assertEqual(environment["VSVIG_ASSET_DIR"], "/opt/vsvig")
        self.assertEqual(environment["MDS01_NNPACK_ENABLED"], "false")

    def test_pose_worker_runs_only_on_blurred_input_and_validates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blurred = root / "blurred.mp4"
            visual = root / "protected.mp4"
            preview = root / "protected.jpg"
            result_path = root / "metrics.json"
            blurred.write_bytes(b"full-frame-blurred-input")

            payload = {
                "sampled_frames": 5,
                "detected_frames": 3,
                "tracking_stopped": True,
                "visualization": {
                    "available": True,
                    "audio_included": False,
                    "pose_sample_count": 3,
                    "pose_overlay_available": True,
                    "width": 640,
                    "height": 360,
                    "frame_count": 48,
                    "fps": 24.0,
                    "duration_seconds": 2.0,
                },
            }

            def run_worker(command, **_kwargs):
                self.assertEqual(command[4], str(blurred))
                self.assertEqual(command[3], "--pose-preview")
                visual.write_bytes(b"blurred-keypoint-preview")
                preview.write_bytes(b"safe-preview-frame")
                result_path.write_text(json.dumps(payload), encoding="utf-8")

            with patch(
                "backend.app.services.video_privacy_service.subprocess.run",
                side_effect=run_worker,
            ) as run, patch(
                "backend.app.video_detection.visualization.validate_visualization_artifact"
            ):
                stats = _run_pose_preview_worker(
                    blurred,
                    visual,
                    preview,
                    result_path,
                    fps=24.0,
                    width=640,
                    height=360,
                    frame_count=48,
                    duration_seconds=2.0,
                )

            worker_environment = run.call_args.kwargs["env"]
            self.assertNotIn("MDS01_STORAGE_KEY", worker_environment)
            self.assertNotIn("DATABASE_URL", worker_environment)
            self.assertEqual(
                stats,
                {
                    "sampled_frames": 5,
                    "detected_frames": 3,
                    "tracking_stopped": True,
                },
            )

    def test_vsvig_normalization_rejects_non_native_geometry_without_opt_in(self) -> None:
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
            with self.assertRaisesRegex(VideoProcessorError, "match the reviewed 1920x1080"):
                VideoPrivacyProcessor.normalize_for_vsvig(
                    Path(directory) / "source.avi",
                    Path(directory) / "normalized.mp4",
                )

    def test_vsvig_letterbox_preserves_aspect_and_records_padding(self) -> None:
        frame = np.full((480, 640, 3), 7, dtype=np.uint8)
        writers = []

        class Capture:
            reads = 0

            def isOpened(self):
                return True

            def get(self, property_id):
                return 0.0

            def read(self):
                self.reads += 1
                return (True, frame.copy()) if self.reads == 1 else (False, None)

            def release(self):
                return None

        class Writer:
            def __init__(self, path, _fourcc, _fps, _size):
                self.path = Path(path)
                self.path.touch()
                self.frames = []
                writers.append(self)

            def isOpened(self):
                return True

            def write(self, value):
                self.frames.append(value.copy())

            def release(self):
                return None

        fake_cv2 = type(
            "FakeCV2",
            (),
            {
                "CAP_PROP_POS_MSEC": 0,
                "INTER_AREA": 2,
                "INTER_LINEAR": 1,
                "VideoCapture": lambda _path: Capture(),
                "VideoWriter": Writer,
                "VideoWriter_fourcc": staticmethod(lambda *_args: 0),
                "resize": staticmethod(
                    lambda _frame, size, **_kwargs: np.full(
                        (size[1], size[0], 3), 7, dtype=np.uint8
                    )
                ),
            },
        )
        metadata = {"fps": 25.0, "width": 640, "height": 480, "frame_count": 1}
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            sys.modules, {"cv2": fake_cv2}
        ), patch.object(VideoPrivacyProcessor, "_stream_metadata", return_value=metadata), patch.object(
            VideoPrivacyProcessor,
            "preflight",
            return_value={"fps": 25.0, "width": 1920, "height": 1080, "frame_count": 1},
        ):
            result = VideoPrivacyProcessor.normalize_for_vsvig(
                Path(directory) / "source.avi",
                Path(directory) / "normalized.mp4",
                allow_letterbox_adaptation=True,
            )

        self.assertEqual(result["adaptation"], "letterbox")
        self.assertEqual((result["source_width"], result["source_height"]), (640, 480))
        self.assertEqual((result["width"], result["height"]), (1920, 1080))
        self.assertEqual((result["pad_x"], result["pad_y"]), (240, 0))
        self.assertEqual(result["padding_ltrb"], [240, 0, 240, 0])
        self.assertEqual(writers[0].frames[0].shape, (1080, 1920, 3))
        self.assertFalse(writers[0].frames[0][:, :240].any())
        self.assertTrue(writers[0].frames[0][:, 240:-240].all())

    def test_preflight_checks_deadline_after_native_read_returns(self) -> None:
        self.preflight_patch.stop()
        clock = {"now": 0.0}
        captures = []

        class Capture:
            def __init__(self) -> None:
                self.released = False
                captures.append(self)

            def isOpened(self):
                return True

            def get(self, property_id):
                return {5: 24.0, 3: 640, 4: 360, 7: 48}[property_id]

            def read(self):
                clock["now"] = 2.0
                return True, object()

            def release(self):
                self.released = True

        fake_cv2 = type(
            "FakeCV2",
            (),
            {
                "CAP_PROP_FPS": 5,
                "CAP_PROP_FRAME_WIDTH": 3,
                "CAP_PROP_FRAME_HEIGHT": 4,
                "CAP_PROP_FRAME_COUNT": 7,
                "VideoCapture": lambda _path: Capture(),
            },
        )
        with patch.dict(sys.modules, {"cv2": fake_cv2}), patch(
            "backend.app.video_privacy.processor.time.monotonic",
            side_effect=lambda: clock["now"],
        ):
            with self.assertRaisesRegex(VideoProcessorError, "preflight timed out"):
                VideoPrivacyProcessor.preflight(Path("synthetic.mp4"), deadline=1.0)

        self.assertTrue(captures[0].released)

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
            "backend.app.services.video_privacy_service.preflight_video_subprocess",
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

    def test_face_blur_and_pose_preview_profiles_are_supported(self) -> None:
        self.assertEqual(parse_profile("face-redacted"), VideoPrivacyProfile.FACE_REDACTED)
        self.assertEqual(
            parse_profile("face-redacted-pose-preview"),
            VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW,
        )
        with self.assertRaisesRegex(ValueError, "Only available"):
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

    def test_truncated_source_cannot_be_published_ready_or_create_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            root = Path(directory) / "sessions"
            storage = VideoStorage(root, storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(
                    create_video_job(db, storage, self._upload(), VideoPrivacyProfile.FACE_REDACTED)
                )
                job_id = job.job_id

            class FakeCapture:
                def __init__(self, path: str) -> None:
                    self.path = path
                    self.read_count = 0

                def isOpened(self) -> bool:
                    return True

                def get(self, property_id: int) -> float:
                    if property_id == 5:
                        return 24.0
                    if property_id == 3:
                        return 4
                    if property_id == 4:
                        return 4
                    if property_id == 7:
                        return 4
                    if property_id == 0:
                        return max(0, self.read_count - 1) * 1000 / 24
                    return 0.0

                def read(self):
                    if self.read_count >= 2:
                        return False, None
                    self.read_count += 1
                    return True, np.zeros((4, 4, 3), dtype=np.uint8)

                def release(self) -> None:
                    return None

            class FakeWriter:
                def __init__(self, path: str, *_args) -> None:
                    self.path = Path(path)
                    self.path.write_bytes(b"")

                def isOpened(self) -> bool:
                    return True

                def write(self, _frame) -> None:
                    self.path.write_bytes(self.path.read_bytes() + b"frame")

                def release(self) -> None:
                    return None

            class FaceDetector:
                @staticmethod
                def empty() -> bool:
                    return False

                @staticmethod
                def detectMultiScale(*_args, **_kwargs):
                    return [(0, 0, 1, 1)]

            class FakeCV2:
                CAP_PROP_FPS = 5
                CAP_PROP_FRAME_WIDTH = 3
                CAP_PROP_FRAME_HEIGHT = 4
                CAP_PROP_FRAME_COUNT = 7
                CAP_PROP_POS_MSEC = 0
                COLOR_BGR2GRAY = 1
                data = type("Data", (), {"haarcascades": "."})
                VideoCapture = FakeCapture
                VideoWriter = FakeWriter
                CascadeClassifier = lambda _path: FaceDetector()
                VideoWriter_fourcc = staticmethod(lambda *_args: 0)
                cvtColor = staticmethod(lambda frame, _code: frame)
                GaussianBlur = staticmethod(lambda frame, *_args, **_kwargs: frame)

                @staticmethod
                def imwrite(path: str, _frame) -> bool:
                    Path(path).write_bytes(b"synthetic-preview")
                    return True

            with patch("backend.app.services.video_privacy_service.engine", database), patch.dict(
                sys.modules,
                {"cv2": FakeCV2},
            ):
                process_video_privacy_job(job_id, storage=storage, processor=VideoPrivacyProcessor())

            with Session(database) as db:
                saved = db.exec(
                    select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
                ).one()
                self.assertEqual(saved.status, VideoPrivacyStatus.FAILED)
                self.assertIsNone(saved.output_path)
                self.assertFalse(saved.output_usable)
            self.assertFalse((root / job_id / "retained").exists())
            self.assertFalse(any((root / job_id).rglob("*preview*")))

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
                self.assertIsNone(job.original_path)
                self.assertEqual(public_video_job(db, job)["profile"], "face-redacted")
            job_root = root / job_id
            self.assertFalse((job_root / "original").exists())
            self.assertFalse((job_root / "work").exists())
            self.assertTrue((job_root / "retained" / "video.output.mp4.enc").exists())
            self.assertTrue((job_root / "retained" / "video.preview.jpg.enc").exists())
            self.assertNotEqual((job_root / "retained" / "video.output.mp4.enc").read_bytes(), b"transformed-video-without-audio")
            self.assertNotIn(b"private-audio", (job_root / "retained" / "video.output.mp4.enc").read_bytes())

    def test_pose_preview_blurs_before_worker_and_retains_only_encrypted_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = self._database()
            root = Path(directory) / "sessions"
            storage = VideoStorage(root, storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(
                    create_video_job(
                        db,
                        storage,
                        self._upload(),
                        VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW,
                    )
                )
                job_id = job.job_id

            def render_pose(source, visual, preview, _metrics, **_expected):
                self.assertEqual(source.read_bytes(), b"transformed-video-without-audio")
                visual.write_bytes(b"blurred-pose-overlay")
                preview.write_bytes(b"blurred-pose-frame")
                return {
                    "sampled_frames": 5,
                    "detected_frames": 3,
                    "tracking_stopped": True,
                }

            processor = FakeProcessor()
            with patch("backend.app.services.video_privacy_service.engine", database), patch(
                "backend.app.services.video_privacy_service._run_pose_preview_worker",
                side_effect=render_pose,
            ), patch(
                "backend.app.services.video_privacy_service.finalize_protected_video",
                side_effect=lambda _source, visual, output: output.write_bytes(
                    visual.read_bytes()
                ),
            ):
                process_video_privacy_job(
                    job_id,
                    storage=storage,
                    processor=processor,
                )

            self.assertTrue(processor.allow_full_blur_fallback)
            with Session(database) as db:
                job = db.exec(
                    select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
                ).one()
                public = public_video_job(db, job)
                self.assertEqual(job.status, VideoPrivacyStatus.NEEDS_REVIEW)
                self.assertEqual(job.pose_detected_frames, 3)
                self.assertEqual(job.pose_sampled_frames, 5)
                self.assertIn("pose_tracking_stopped", job.quality_flags())
                self.assertEqual(public["pose_evidence"]["detected_frames"], 3)
                self.assertNotIn("pose_samples", public)
                self.assertNotIn("keypoint_coordinates", public)

            job_root = root / job_id
            self.assertFalse((job_root / "original").exists())
            self.assertFalse((job_root / "work").exists())
            self.assertTrue((job_root / "retained" / "video.output.mp4.enc").exists())
            self.assertTrue((job_root / "retained" / "video.preview.jpg.enc").exists())

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

    def test_expiry_lock_compiles_to_postgresql_row_lock(self) -> None:
        from sqlalchemy.dialects import postgresql

        statement = _privacy_job_lock_statement("VID-SYNTHETIC").compile(
            dialect=postgresql.dialect()
        )
        self.assertIn("FOR UPDATE", str(statement).upper())

    def test_expiry_sweep_cannot_be_overwritten_by_worker_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = create_engine(
                f"sqlite:///{root / 'privacy-race.sqlite3'}",
                connect_args={"check_same_thread": False},
            )
            SQLModel.metadata.create_all(database)
            storage = VideoStorage(root / "sessions", storage_key=self.storage_key)
            with Session(database) as db:
                job = asyncio.run(
                    create_video_job(
                        db,
                        storage,
                        self._upload(),
                        VideoPrivacyProfile.FACE_REDACTED,
                    )
                )
                job_id = job.job_id

            finalizing = threading.Event()
            resume_worker = threading.Event()

            def pause_finalization(_source: Path, visual: Path, output: Path) -> None:
                visual_bytes = visual.read_bytes()
                preview = visual.with_name("video.preview.jpg")
                preview_bytes = preview.read_bytes()
                finalizing.set()
                if not resume_worker.wait(timeout=10):
                    raise TimeoutError("test worker was not resumed")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(visual_bytes)
                preview.write_bytes(preview_bytes)

            worker_errors: list[BaseException] = []

            def run_worker() -> None:
                try:
                    process_video_privacy_job(
                        job_id,
                        storage=storage,
                        processor=FakeProcessor(),
                    )
                except BaseException as exc:  # surfaced in the test thread
                    worker_errors.append(exc)

            worker = threading.Thread(target=run_worker)
            with (
                patch("backend.app.services.video_privacy_service.engine", database),
                patch("backend.app.services.video_privacy_service.VideoStorage", return_value=storage),
                patch(
                    "backend.app.services.video_privacy_service.finalize_protected_video",
                    side_effect=pause_finalization,
                ),
            ):
                worker.start()
                try:
                    self.assertTrue(finalizing.wait(timeout=10), "worker did not reach publication")
                    with Session(database) as db:
                        job = db.exec(
                            select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
                        ).one()
                        job.retention_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                        db.add(job)
                        db.commit()
                    sweep_video_privacy_jobs()
                finally:
                    resume_worker.set()
                    worker.join(timeout=10)

            self.assertFalse(worker.is_alive(), "worker did not finish")
            self.assertEqual(worker_errors, [])
            with Session(database) as db:
                saved = db.exec(
                    select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
                ).one()
                self.assertEqual(saved.status, VideoPrivacyStatus.FAILED)
                self.assertFalse(saved.output_usable)
                self.assertIsNone(saved.output_path)
                self.assertIsNone(saved.preview_path)
            self.assertFalse((storage.root / job_id).exists())
            database.dispose()

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
