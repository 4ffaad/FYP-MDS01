"""Video-only contract, ownership, ciphertext, range playback, and cleanup checks."""

import asyncio
import base64
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from backend.app.database.db import get_session
from backend.app.database.models.video import utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.core.config import STORAGE_KEY_ENV
from backend.app.eeg.legacy_nicolet import video_sync_name_token
from backend.app.main import app
from backend.app.services import video_detection_service as service
from backend.app.services.auth_service import ensure_demo_admin
from backend.app.services.video_storage_service import VideoStorage
from backend.app.services.video_sync_service import (
    decrypt_sync_payload,
    encrypt_job_mapping,
    match_sync_video_group,
)
from backend.app.video_detection.contract import DetectionError, digest, load_contract, validate_predictions
from backend.app.video_detection.runtime import (
    _last_model_sample_index,
    _missing_required_keypoints,
    _validate_required_keypoints,
    blur_rgb_patches,
)

POSE_READY = {
    "ready": True,
    "checked_frames": 30,
    "required_frames": 30,
    "window_seconds": 5,
    "frames_without_person": 0,
    "frames_with_multiple_people": 0,
    "frames_with_tracking_break": 0,
    "frames_with_incomplete_pose": 0,
    "missing_landmarks": {},
}


class VideoRuntimeKeypointValidationTests(unittest.TestCase):
    def test_unused_trailing_samples_do_not_fail_a_complete_model_window(self):
        self.assertEqual(_last_model_sample_index(31, 30, 3), 29)
        self.assertEqual(_last_model_sample_index(33, 30, 3), 32)
        self.assertEqual(_last_model_sample_index(36, 30, 3), 35)
        self.assertEqual(_last_model_sample_index(29, 30, 3), -1)

    def test_missing_unused_openpose_points_do_not_block_vsvig_input(self):
        import numpy as np

        keypoints = np.zeros((18, 3), dtype=np.float32)
        keypoints[:, :2] = 100
        keypoints[:, 2] = 0.9
        keypoints[[1, 16, 17]] = (-1, -1, 0)

        _validate_required_keypoints(
            keypoints, [index for index in range(18) if index not in (1, 16, 17)],
            1920, 1080, 0.1,
        )

    def test_low_confidence_required_point_blocks_inference(self):
        import numpy as np

        keypoints = np.zeros((18, 3), dtype=np.float32)
        keypoints[:, :2] = 100
        keypoints[:, 2] = 0.9
        keypoints[14, 2] = 0.05

        with self.assertRaisesRegex(DetectionError, "incomplete_pose"):
            _validate_required_keypoints(
                keypoints, [index for index in range(18) if index not in (1, 16, 17)],
                1920, 1080, 0.1,
            )

    def test_readiness_gate_reports_an_out_of_frame_selected_ankle(self):
        import numpy as np

        keypoints = np.zeros((18, 3), dtype=np.float32)
        keypoints[:, :2] = 100
        keypoints[:, 2] = 0.9
        keypoints[13, 1] = 1080

        missing = _missing_required_keypoints(
            keypoints, [index for index in range(18) if index not in (1, 16, 17)],
            1920, 1080, 0.1,
        )

        self.assertEqual(missing, [13])

    def test_pose_rejection_message_names_missing_landmarks_without_coordinates(self):
        from backend.app.video_detection.contract import DetectionError

        detail = service.detection_error_detail(
            DetectionError(
                "pose_readiness_landmarks",
                details={
                    "pose_readiness": {
                        **POSE_READY,
                        "ready": False,
                        "frames_with_incomplete_pose": 1,
                        "missing_landmarks": {"right ankle": 1},
                    }
                },
            )
        )

        self.assertIn("right ankle: 1", detail)
        self.assertNotIn("coordinates", detail)


class VideoEegSyncMatchingTests(unittest.TestCase):
    def test_sync_group_maps_across_an_eeg_gap_using_video_frames(self):
        manifest = {
            "segments": [
                {"source_start_seconds": 0.0, "duration_seconds": 100.0},
                {"source_start_seconds": 200.0, "duration_seconds": 100.0},
            ],
            "markers": [
                {"source_name_token": "a" * 64, "frame_index": 0, "eeg_clock_seconds": 1.0},
                {"source_name_token": "a" * 64, "frame_index": 25, "eeg_clock_seconds": 2.0},
                {"source_name_token": "a" * 64, "frame_index": 50, "eeg_clock_seconds": 3.0},
                {"source_name_token": "b" * 64, "frame_index": 0, "eeg_clock_seconds": 200.5},
                {"source_name_token": "b" * 64, "frame_index": 25, "eeg_clock_seconds": 201.5},
            ],
        }
        jobs = [
            SimpleNamespace(source_name_token="a" * 64, fps=25.0, duration_seconds=2.04, job_id="VID-A"),
            SimpleNamespace(source_name_token="b" * 64, fps=25.0, duration_seconds=1.04, job_id="VID-B"),
        ]

        links = match_sync_video_group(manifest, jobs)

        self.assertIsNotNone(links)
        assert links is not None
        self.assertAlmostEqual(links["VID-A"]["eeg_source_start_seconds"], 1.0)
        self.assertAlmostEqual(
            links["VID-A"]["mapped_segments"][0]["eeg_source_start_seconds"], 1.0
        )
        self.assertAlmostEqual(links["VID-B"]["eeg_source_start_seconds"], 200.5)
        self.assertAlmostEqual(
            links["VID-B"]["mapped_segments"][0]["eeg_source_start_seconds"], 200.5
        )
        self.assertEqual(links["VID-B"]["video_duration_seconds"], 1.04)
        self.assertAlmostEqual(links["VID-B"]["eeg_coverage_seconds"], 1.04)

    def test_sync_mapping_splits_video_spanning_an_eeg_acquisition_gap(self):
        manifest = {
            "segments": [
                {"source_start_seconds": 0.0, "duration_seconds": 100.0},
                {"source_start_seconds": 200.0, "duration_seconds": 100.0},
            ],
            "markers": [
                {"source_name_token": "a" * 64, "frame_index": 0, "eeg_clock_seconds": 99.0},
                {"source_name_token": "a" * 64, "frame_index": 2549, "eeg_clock_seconds": 200.96},
            ],
        }
        job = SimpleNamespace(
            source_name_token="a" * 64,
            fps=25.0,
            duration_seconds=102.0,
            job_id="VID-GAP",
        )

        links = match_sync_video_group(manifest, [job])

        self.assertIsNotNone(links)
        assert links is not None
        self.assertEqual(len(links["VID-GAP"]["mapped_segments"]), 2)
        self.assertEqual(
            links["VID-GAP"]["mapped_segments"],
            [
                {
                    "video_start_seconds": 0.0,
                    "video_end_seconds": 1.0,
                    "eeg_source_start_seconds": 99.0,
                },
                {
                    "video_start_seconds": 101.0,
                    "video_end_seconds": 102.0,
                    "eeg_source_start_seconds": 200.0,
                },
            ],
        )
        self.assertAlmostEqual(links["VID-GAP"]["eeg_coverage_seconds"], 2.0)

    def test_sync_mapping_keeps_video_time_when_clip_starts_before_eeg(self):
        manifest = {
            "segments": [{"source_start_seconds": 0.0, "duration_seconds": 10.0}],
            "markers": [
                {"source_name_token": "a" * 64, "frame_index": 0, "eeg_clock_seconds": -1.0},
                {"source_name_token": "a" * 64, "frame_index": 50, "eeg_clock_seconds": 1.0},
            ],
        }
        job = SimpleNamespace(
            source_name_token="a" * 64,
            fps=25.0,
            duration_seconds=2.04,
            job_id="VID-PRE-EEG",
        )

        links = match_sync_video_group(manifest, [job])

        self.assertIsNotNone(links)
        assert links is not None
        self.assertAlmostEqual(links["VID-PRE-EEG"]["eeg_source_start_seconds"], -1.0)
        self.assertEqual(
            links["VID-PRE-EEG"]["mapped_segments"],
            [
                {
                    "video_start_seconds": 1.0,
                    "video_end_seconds": 2.04,
                    "eeg_source_start_seconds": 0.0,
                }
            ],
        )

    def test_one_complete_camera_folder_can_map_disjoint_clips_to_two_eegs(self):
        jobs = [
            SimpleNamespace(source_name_token="a" * 64, fps=25.0, duration_seconds=1.04, job_id="VID-A"),
            SimpleNamespace(source_name_token="b" * 64, fps=25.0, duration_seconds=1.04, job_id="VID-B"),
        ]
        first = match_sync_video_group(
            {
                "segments": [{"source_start_seconds": 0.0, "duration_seconds": 100.0}],
                "markers": [
                    {"source_name_token": "a" * 64, "frame_index": 0, "eeg_clock_seconds": 1.0},
                    {"source_name_token": "a" * 64, "frame_index": 25, "eeg_clock_seconds": 2.0},
                ],
            },
            jobs,
        )
        second = match_sync_video_group(
            {
                "segments": [{"source_start_seconds": 200.0, "duration_seconds": 100.0}],
                "markers": [
                    {"source_name_token": "b" * 64, "frame_index": 0, "eeg_clock_seconds": 201.0},
                    {"source_name_token": "b" * 64, "frame_index": 25, "eeg_clock_seconds": 202.0},
                ],
            },
            jobs,
        )

        self.assertEqual(set(first or {}), {"VID-A"})
        self.assertEqual(set(second or {}), {"VID-B"})

    def test_sync_group_fails_closed_on_bad_frame_count_or_duplicate_name(self):
        manifest = {
            "segments": [{"source_start_seconds": 0.0, "duration_seconds": 100.0}],
            "markers": [
                {"source_name_token": "a" * 64, "frame_index": 0, "eeg_clock_seconds": 1.0},
                {"source_name_token": "a" * 64, "frame_index": 25, "eeg_clock_seconds": 2.0},
            ],
        }
        valid_job = SimpleNamespace(source_name_token="a" * 64, fps=25.0, duration_seconds=1.04, job_id="VID-A")
        wrong_duration = SimpleNamespace(source_name_token="a" * 64, fps=25.0, duration_seconds=20.0, job_id="VID-B")

        self.assertIsNone(match_sync_video_group(manifest, [wrong_duration]))
        self.assertIsNone(match_sync_video_group(manifest, [valid_job, wrong_duration]))


class VideoEegSyncEncryptionTests(unittest.TestCase):
    def test_job_clock_mapping_is_encrypted_and_bound_to_owner_case_and_job(self):
        owner_key = base64.b64encode(b"s" * 32).decode("ascii")
        job = SimpleNamespace(job_id="VID-SYNC-1", eeg_sync_nonce=None, eeg_sync_ciphertext=None)
        mapping = {
            "eeg_source_start_seconds": 12.5,
            "mapped_segments": [
                {
                    "video_start_seconds": 0.0,
                    "video_end_seconds": 10.0,
                    "eeg_source_start_seconds": 12.5,
                }
            ],
        }
        with patch.dict(os.environ, {STORAGE_KEY_ENV: owner_key}):
            encrypt_job_mapping(
                job,
                owner_user_id=7,
                case_id="CASE-SAFE",
                mapping=mapping,
            )
            self.assertNotIn(b"12.5", job.eeg_sync_ciphertext)
            self.assertEqual(
                decrypt_sync_payload(
                    "video-job", 7, "CASE-SAFE", job.job_id,
                    job.eeg_sync_nonce, job.eeg_sync_ciphertext,
                ),
                mapping,
            )
            self.assertIsNone(
                decrypt_sync_payload(
                    "video-job", 8, "CASE-SAFE", job.job_id,
                    job.eeg_sync_nonce, job.eeg_sync_ciphertext,
                )
            )


class VideoDetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = VideoStorage(Path(self.temp.name) / "sessions", storage_key=os.urandom(32))
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        def sessions():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_session] = sessions
        self.addCleanup(app.dependency_overrides.pop, get_session)
        for target, value in (("backend.app.api.video_detection.VideoStorage", lambda: self.storage),
                              ("backend.app.services.video_detection_service.VideoStorage", lambda: self.storage),
                              ("backend.app.services.video_detection_service.engine", self.engine)):
            p = patch(target, value); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, {"APP_ENV": "test", "AUTH_MODE": "local-accounts", "VIDEO_DETECTION_ENABLED": "true"})
        p.start(); self.addCleanup(p.stop)
        p = patch.object(service, "_run_pose_readiness", return_value=POSE_READY)
        p.start(); self.addCleanup(p.stop)
        # No application lifespan: dependencies and database are fixture-scoped.
        self.alice, self.bob = TestClient(app), TestClient(app)
        self.addCleanup(self.alice.close); self.addCleanup(self.bob.close)
        self.headers = {"Origin": "http://localhost:3000"}
        for client, email in ((self.alice, "alice@example.test"), (self.bob, "bob@example.test")):
            response = client.post("/api/auth/register", json={"email": email, "password": os.urandom(16).hex()}, headers=self.headers)
            self.assertEqual(response.status_code, 201, response.text)
        with Session(self.engine) as db:
            from backend.app.database.models.auth import User
            self.owner = db.exec(select(User).where(User.email == "alice@example.test")).one().id

    def seed(self, status="ready", with_visualization=False, prediction_overrides=None):
        with Session(self.engine) as db:
            job = VideoDetectionJob(owner_user_id=self.owner, job_id="VID-" + os.urandom(16).hex(), status=status,
                                    duration_seconds=10, fps=30, retention_expires_at=utc_now() + timedelta(hours=1))
            results = self.storage.work_path(job.job_id, "predictions.json")
            prediction_result = validate_predictions([
                {"start_time": 0, "end_time": 2, "raw_score": 0.8},
            ], 10, {"threshold": 0.5})
            prediction_result.update(prediction_overrides or {})
            results.write_text(json.dumps(prediction_result))
            job.predictions_path = str(self.storage.store_artifact(job.job_id, results, "predictions.json"))
            if with_visualization:
                visualization = self.storage.work_path(job.job_id, "privacy-safe-review.mp4")
                visualization.write_bytes(b"protected-review-video")
                job.visualization_path = str(self.storage.store_artifact(job.job_id, visualization, "video.visualization.mp4"))
            db.add(job); db.commit(); db.refresh(job)
            return job.job_id

    def test_video_sync_headers_are_cors_allowed_and_never_echoed(self):
        preflight = self.alice.options(
            "/api/video-detection/jobs",
            headers={
                **self.headers,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "content-type,x-case-id,x-model-blur-percent,x-video-format,"
                    "x-veeg-source-name,x-veeg-source-group"
                ),
            },
        )
        self.assertEqual(preflight.status_code, 200, preflight.text)
        allowed_headers = preflight.headers.get("access-control-allow-headers", "").lower()
        self.assertIn("x-veeg-source-name", allowed_headers)
        self.assertIn("x-veeg-source-group", allowed_headers)

        case_id = "CASE-SYNC-HEADER-TEST"
        job = VideoDetectionJob(
            owner_user_id=self.owner,
            case_id=case_id,
            job_id="VID-SYNC-HEADER-TEST",
            status="failed",
            retention_expires_at=utc_now() + timedelta(hours=1),
        )
        with patch.object(
            service,
            "create_job",
            new=AsyncMock(return_value=job),
        ) as create_job:
            response = self.alice.post(
                "/api/video-detection/jobs",
                content=b"synthetic-video-bytes",
                headers={
                    **self.headers,
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "avi",
                    "X-Case-ID": case_id,
                    "X-VEEG-Source-Name": "Private%20recording.avi",
                    "X-VEEG-Source-Group": "123e4567-e89b-12d3-a456-426614174000",
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(create_job.call_args.args[6], "Private recording.avi")
        self.assertNotIn("Private recording.avi", response.text)

    def test_sync_group_cannot_be_closed_before_all_expected_clips_are_uploaded(self):
        from uuid import uuid4

        case_id = "CASE-AABBCCDD"
        group_id = str(uuid4())
        clip_names = ["clip-01.avi", "clip-02.avi"]
        storage_key = base64.b64encode(b"s" * 32).decode("ascii")
        with Session(self.engine) as db:
            db.add_all(
                VideoDetectionJob(
                    owner_user_id=self.owner,
                    case_id=case_id,
                    job_id=f"VID-SYNC-COMPLETE-{index}",
                    source_name_token=video_sync_name_token(
                        clip_names[index],
                        base64.b64decode(storage_key),
                        context=f"{self.owner}:{case_id}",
                    ),
                    source_group_id=group_id,
                    retention_expires_at=utc_now() + timedelta(hours=1),
                )
                for index in range(2)
            )
            db.commit()

        with patch.dict(os.environ, {STORAGE_KEY_ENV: storage_key}):
            incomplete = self.alice.post(
                f"/api/video-detection/cases/{case_id}/sync-groups/{group_id}/finalize",
                json={"expected_source_names": clip_names + ["clip-03.avi"]},
                headers=self.headers,
            )
        self.assertEqual(incomplete.status_code, 409, incomplete.text)
        with Session(self.engine) as db:
            self.assertFalse(
                any(
                    job.sync_group_complete
                    for job in db.exec(
                        select(VideoDetectionJob).where(
                            VideoDetectionJob.source_group_id == group_id
                        )
                    ).all()
                )
            )

        with patch.dict(os.environ, {STORAGE_KEY_ENV: storage_key}):
            complete = self.alice.post(
                f"/api/video-detection/cases/{case_id}/sync-groups/{group_id}/finalize",
                json={"expected_source_names": clip_names},
                headers=self.headers,
            )
        self.assertEqual(complete.status_code, 200, complete.text)

    def test_video_preflight_exact_body_cap_rejects_early_with_cors(self):
        with patch("backend.app.core.middleware.MAX_VIDEO_UPLOAD_BYTES", 3), patch(
            "backend.app.core.middleware.REQUEST_BODY_OVERHEAD_BYTES", 1024
        ), patch(
            "backend.app.api.video_detection.service.preflight_video_upload",
            new=AsyncMock(return_value={"accepted": True}),
        ) as preflight:
            response = self.alice.post(
                "/api/video-detection/preflight",
                content=b"four",
                headers={
                    **self.headers,
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "mp4",
                    "Content-Length": "4",
                },
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")
        preflight.assert_not_awaited()

    def test_chunked_video_preflight_over_limit_preserves_typed_413(self):
        with patch("backend.app.core.middleware.MAX_VIDEO_UPLOAD_BYTES", 3), patch(
            "backend.app.core.middleware.REQUEST_BODY_OVERHEAD_BYTES", 1024
        ), patch(
            "backend.app.api.video_detection.service._preflight_uploaded_video",
            return_value={"fps": 24.0, "width": 1920, "height": 1080, "frame_count": 48},
        ) as preflight:
            response = self.alice.post(
                "/api/video-detection/preflight",
                content=iter((b"ab", b"cd")),
                headers={
                    **self.headers,
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "mp4",
                },
            )

        self.assertNotIn("content-length", response.request.headers)
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")
        preflight.assert_not_called()

    def test_vsvig_subprocess_receives_runtime_allowlist_not_backend_secrets(self):
        with patch.dict(
            os.environ,
            {
                "MDS01_STORAGE_KEY": "synthetic-storage-secret",
                "MDS01_TEMPLATE_KEY": "synthetic-template-secret",
                "DATABASE_URL": "postgresql://synthetic-private-db",
                "STORAGE_DIR": "/synthetic/private/storage",
                "AUTH_SECRET": "synthetic-auth-secret",
                "CLOUDFLARE_ACCESS_AUD": "synthetic-audience",
                "VSVIG_ASSET_DIR": "/opt/synthetic-vsvig",
                "VSVIG_CONTRACT_SHA256": "a" * 64,
                "MDS01_NNPACK_ENABLED": "false",
            },
            clear=True,
        ), patch.object(service.subprocess, "run") as run:
            service.execute(["python", "-m", "backend.app.video_detection.runtime"], timeout=5)

        environment = run.call_args.kwargs.get("env")
        self.assertIsNotNone(environment)
        for secret_name in (
            "MDS01_STORAGE_KEY",
            "MDS01_TEMPLATE_KEY",
            "DATABASE_URL",
            "STORAGE_DIR",
            "AUTH_SECRET",
            "CLOUDFLARE_ACCESS_AUD",
        ):
            self.assertNotIn(secret_name, environment)
        self.assertEqual(environment["VSVIG_ASSET_DIR"], "/opt/synthetic-vsvig")
        self.assertEqual(environment["VSVIG_CONTRACT_SHA256"], "a" * 64)
        self.assertEqual(environment["MDS01_NNPACK_ENABLED"], "false")
        self.assertEqual(environment["PYTHONPATH"], str(Path(service.__file__).resolve().parents[3]))

    def test_auth_ownership_and_no_private_metadata(self):
        job_id = self.seed()
        for suffix in ("", "/predictions", "/visualization"):
            self.assertEqual(self.bob.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 404)
            with TestClient(app) as anon:
                self.assertEqual(anon.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 401)
        self.assertEqual(self.bob.get("/api/video-detection/jobs").json(), {"jobs": []})
        response = self.alice.get(f"/api/video-detection/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("path", response.text)
        self.assertNotIn(self.temp.name, response.text)

    def test_prediction_response_filters_legacy_source_timing_metadata(self):
        job_id = self.seed(
            prediction_overrides={
                "duration_seconds": 10.0,
                "fps": 30.0,
                "frame_count": 300,
                "source_filename": "synthetic-source.mp4",
                "private_source_path": "/synthetic/private/source.mp4",
                "model": {
                    "threshold": 0.5,
                    "contract_version": "synthetic-contract-v1",
                    "private_source_path": "/synthetic/private/model-source.mp4",
                },
                "predictions": [
                    {
                        "start_time": 0.0,
                        "end_time": 2.0,
                        "raw_score": 0.8,
                        "score": 0.8,
                        "score_type": "uncalibrated_model_score",
                        "seizure_detected": True,
                        "threshold": 0.5,
                        "private_source_path": "/synthetic/private/window-source.mp4",
                        "model_evidence": {
                            "method": "patch-occlusion",
                            "note": "Synthetic non-clinical sensitivity evidence.",
                            "patches": [
                                {
                                    "patch_index": index,
                                    "component": f"patch-{index}",
                                    "score_change": index / 100,
                                    "private_source_path": "/synthetic/private/patch.mp4",
                                }
                                for index in range(15)
                            ],
                            "pose_samples": [
                                {
                                    "timestamp": 1.0,
                                    "points": [
                                        {
                                            "patch_index": index,
                                            "x": 0.5,
                                            "y": 0.4,
                                            "confidence": 0.9,
                                            "private_source_path": "/synthetic/private/point.mp4",
                                        }
                                        for index in range(15)
                                    ],
                                    "private_source_path": "/synthetic/private/sample.mp4",
                                }
                            ],
                            "private_source_path": "/synthetic/private/evidence.mp4",
                        },
                    }
                ],
                "privacy": {
                    "method": "face-detection-and-full-frame-blur",
                    "model_input": "15 individually blurred RGB patches per sampled frame",
                    "source_timestamp_offset_seconds": 1234.567,
                    "private_source_path": "/synthetic/private/privacy-source.mp4",
                    "face_detection_coverage": 1.0,
                    "face_blur_coverage": 0.8,
                    "quality_flags": [],
                    "review_required": False,
                },
            }
        )

        response = self.alice.get(f"/api/video-detection/jobs/{job_id}/predictions")

        self.assertEqual(response.status_code, 200, response.text)
        public_result = response.json()
        self.assertNotIn("source_filename", public_result)
        self.assertNotIn("private_source_path", public_result)
        self.assertNotIn("/synthetic/private/", json.dumps(public_result))
        self.assertNotIn("source_timestamp_offset_seconds", json.dumps(public_result))
        self.assertNotIn(
            "source_timestamp_offset_seconds", public_result.get("privacy", {})
        )
        self.assertEqual(
            public_result["model"]["contract_version"], "synthetic-contract-v1"
        )
        self.assertEqual(public_result["privacy"]["face_detection_coverage"], 1.0)
        self.assertEqual(public_result["privacy"]["face_blur_coverage"], 0.8)
        self.assertEqual(public_result["predictions"][0]["score"], 0.8)
        self.assertEqual(
            len(public_result["predictions"][0]["model_evidence"]["pose_samples"][0]["points"]),
            15,
        )
        evidence = public_result["predictions"][0]["model_evidence"]
        self.assertEqual(evidence["method"], "patch-occlusion")
        self.assertEqual(evidence["note"], "Synthetic non-clinical sensitivity evidence.")
        self.assertEqual(len(evidence["patches"]), 15)
        self.assertEqual(
            evidence["patches"][0],
            {"patch_index": 0, "component": "patch-0", "score_change": 0.0},
        )

    def test_demo_admin_can_read_other_users_video_detection_jobs(self):
        job_id = self.seed()
        admin_password = os.urandom(16).hex()
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "AUTH_MODE": "local-accounts",
                "DEMO_ADMIN_ENABLED": "true",
                "DEMO_ADMIN_PASSWORD": admin_password,
            },
        ), Session(self.engine) as db:
            ensure_demo_admin(db)
            admin = TestClient(app)
            self.addCleanup(admin.close)
            login = admin.post(
                "/api/auth/login",
                json={"email": "admin@mds01.local", "password": admin_password},
                headers=self.headers,
            )
            self.assertEqual(login.status_code, 200, login.text)
            self.assertEqual(admin.get(f"/api/video-detection/jobs/{job_id}").status_code, 200)
            self.assertEqual(
                [item["job_id"] for item in admin.get("/api/video-detection/jobs").json()["jobs"]],
                [job_id],
            )

    def test_admin_flag_is_owner_scoped_outside_development_demo_mode(self):
        job_id = self.seed()
        with Session(self.engine) as db:
            from backend.app.database.models.auth import User

            bob = db.exec(select(User).where(User.email == "bob@example.test")).one()
            bob.is_admin = True
            db.add(bob)
            db.commit()
        with patch.dict(os.environ, {"APP_ENV": "development", "AUTH_MODE": "local-accounts", "DEMO_ADMIN_ENABLED": "false"}):
            response = self.bob.get(f"/api/video-detection/jobs/{job_id}")
        self.assertEqual(response.status_code, 404)

    def test_visualization_is_owner_scoped_and_supports_range_playback(self):
        job_id = self.seed(with_visualization=True)
        self.assertEqual(
            self.bob.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            404,
        )
        with TestClient(app) as anon:
            self.assertEqual(
                anon.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
                401,
            )

        response = self.alice.get(
            f"/api/video-detection/jobs/{job_id}/visualization",
            headers={"Range": "bytes=0-8"},
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"protected")
        self.assertEqual(response.headers["content-range"], "bytes 0-8/22")
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertIn("no-store", response.headers["cache-control"])
        self.assertTrue(self.alice.get(f"/api/video-detection/jobs/{job_id}").json()["job"]["video_available"])

    def test_failed_job_can_keep_owner_scoped_redacted_review_without_scores(self):
        job_id = self.seed(status="failed", with_visualization=True)
        response = self.alice.get(f"/api/video-detection/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["job"]["video_available"])
        self.assertEqual(response.json()["job"]["status"], "failed")
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/predictions").status_code,
            409,
        )
        self.assertEqual(
            self.bob.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            404,
        )
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            200,
        )
        service.sweep()
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            200,
        )

    def test_admission_failure_review_copy_is_encrypted_and_source_is_deleted(self):
        job_id = "VID-" + os.urandom(16).hex()
        with Session(self.engine) as db:
            encrypted = asyncio.run(
                self.storage.save_upload(
                    job_id,
                    UploadFile(
                        filename="clip.avi",
                        file=io.BytesIO(b"private-source-bytes"),
                        headers=Headers({"content-type": "video/x-msvideo"}),
                    ),
                )
            )
            job = VideoDetectionJob(
                owner_user_id=self.owner,
                job_id=job_id,
                status="processing",
                current_stage="privacy-review",
                original_path=str(encrypted),
                fps=25,
                duration_seconds=10,
                retention_expires_at=utc_now() + timedelta(hours=1),
            )
            db.add(job)
            db.commit()

            class ReviewProcessor:
                def process(self, source, visual, preview, profile, **kwargs):
                    self_source = source.read_bytes()
                    self_seen = (
                        getattr(profile, "value", profile),
                        kwargs.get("allow_full_blur_fallback"),
                    )
                    self.assertions = (self_source, self_seen)
                    visual.write_bytes(b"face-redacted-video")
                    preview.write_bytes(b"preview")
                    return SimpleNamespace(
                        usable=True,
                        fps=25.0,
                        width=640,
                        height=480,
                        frame_count=250,
                        duration_seconds=10.0,
                    )

            processor = ReviewProcessor()
            with patch(
                "backend.app.services.video_privacy_service.finalize_protected_video",
                side_effect=lambda _source, visual, output: output.write_bytes(
                    visual.read_bytes() + b"-h264"
                ),
            ), patch.object(service, "validate_visualization_artifact"):
                self.assertTrue(
                    service._make_private_review_copy(
                        db, self.storage, job, processor=processor
                    )
                )
            self.assertEqual(processor.assertions[0], b"private-source-bytes")
            self.assertEqual(processor.assertions[1], ("face-redacted", True))
            saved = db.exec(
                select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)
            ).one()
            self.assertEqual(saved.status, "failed")
            self.assertEqual(saved.current_stage, "privacy-review-ready")
            self.assertIsNone(saved.original_path)
            encrypted_review = Path(saved.visualization_path or "")
            self.assertTrue(encrypted_review.is_file())
            self.assertNotIn(b"face-redacted-video", encrypted_review.read_bytes())
            self.assertFalse((self.storage.root / job_id / "original").exists())
            self.assertFalse((self.storage.root / job_id / "work").exists())

    def test_expiry_sweep_removes_visualization_and_predictions_without_a_visit(self):
        job_id = self.seed(with_visualization=True)
        with Session(self.engine) as db:
            job = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            job.retention_expires_at = utc_now() - timedelta(seconds=1)
            db.add(job); db.commit()
        service.sweep()
        self.assertFalse((self.storage.root / job_id).exists())
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/video").status_code, 404)
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code, 409)
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/predictions").status_code, 409)

    def test_ready_sweep_removes_other_work_and_keeps_recent_playback_cache(self):
        job_id = self.seed(with_visualization=True)
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            200,
        )
        playback = self.storage.root / job_id / "work" / "visualization-playback.mp4"
        leftover = self.storage.work_path(job_id, "response.mp4")
        leftover.write_bytes(b"plaintext")
        with Session(self.engine) as db:
            job = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            retained_visualization = Path(job.visualization_path or "")

        service.sweep()

        self.assertFalse(leftover.exists())
        self.assertTrue(playback.is_file())
        self.assertTrue(retained_visualization.is_file())
        self.assertNotIn(b"protected-review-video", retained_visualization.read_bytes())

    def test_ready_sweep_removes_idle_playback_cache(self):
        job_id = self.seed(with_visualization=True)
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            200,
        )
        playback = self.storage.root / job_id / "work" / "visualization-playback.mp4"
        marker = self.storage.root / job_id / "work" / "visualization-playback.ready"
        os.utime(playback, (1, 1))
        os.utime(marker, (1, 1))

        service.sweep()

        self.assertFalse(playback.exists())
        self.assertFalse(marker.exists())

    def test_expiry_converts_aware_non_utc_timestamps_before_comparing(self):
        job = VideoDetectionJob(
            job_id="VID-timezone",
            owner_user_id=1,
            retention_expires_at=datetime.now(timezone.utc).astimezone(
                timezone(timedelta(hours=2))
            ) - timedelta(seconds=1),
        )
        self.assertTrue(service.expired(job))

    def test_missing_or_unreviewed_contract_fails_before_storage(self):
        for code in ("assets_missing", "contract_unreviewed", "asset_mismatch"):
            with patch.object(service, "load_contract", side_effect=DetectionError(code)):
                response = self.alice.post(
                    "/api/video-detection/jobs",
                    content=b"test",
                    headers={**self.headers, "Content-Type": "application/octet-stream", "X-Video-Format": "mp4"},
                )
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private-name", response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(VideoDetectionJob)).all(), [])

    def test_invalid_model_blur_strength_is_rejected_before_upload(self):
        for value in ("49", "101", "not-a-number"):
            with self.subTest(value=value):
                response = self.alice.post(
                    "/api/video-detection/jobs",
                    content=b"must-not-be-read",
                    headers={
                        **self.headers,
                        "Content-Type": "application/octet-stream",
                        "X-Video-Format": "mp4",
                        "X-Model-Blur-Percent": value,
                    },
                )
                self.assertEqual(response.status_code, 422)
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(VideoDetectionJob)).all(), [])

    def test_upload_persists_requested_model_blur_strength(self):
        job = VideoDetectionJob(
            owner_user_id=self.owner,
            job_id="VID-BLUR-STRENGTH",
            blur_strength_percent=65,
            retention_expires_at=utc_now() + timedelta(hours=1),
        )
        with patch.object(
            service,
            "create_job",
            new=AsyncMock(return_value=job),
        ) as create_job, patch.object(service, "process_job"):
            response = self.alice.post(
                "/api/video-detection/jobs",
                content=b"synthetic-video-bytes",
                headers={
                    **self.headers,
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "mp4",
                    "X-Model-Blur-Percent": "65",
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["job"]["blur_strength_percent"], 65)
        self.assertEqual(
            create_job.call_args.kwargs["blur_strength_percent"],
            65,
        )

    def test_video_upload_is_accepted_while_another_video_job_is_active(self):
        active = VideoDetectionJob(
            owner_user_id=self.owner,
            job_id="VID-ACTIVE-QUEUE-TEST",
            status="processing",
            retention_expires_at=utc_now() + timedelta(hours=1),
        )
        with Session(self.engine) as db:
            db.add(active)
            db.commit()
        queued = VideoDetectionJob(
            owner_user_id=self.owner,
            job_id="VID-QUEUED-AFTER-ACTIVE",
            retention_expires_at=utc_now() + timedelta(hours=1),
        )
        with patch.object(
            service,
            "create_job",
            new=AsyncMock(return_value=queued),
        ) as create_job, patch.object(service, "process_job"):
            response = self.alice.post(
                "/api/video-detection/jobs",
                content=b"synthetic-video-bytes",
                headers={
                    **self.headers,
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "mp4",
                },
            )
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["job"]["job_id"], queued.job_id)
        create_job.assert_awaited_once()

    def test_model_blur_operates_on_extracted_rgb_patches(self):
        import numpy as np
        from types import SimpleNamespace

        patches = np.zeros((15, 32, 32, 3), dtype=np.uint8)
        patches[:, 16, 16] = 255
        calls = []

        def gaussian_blur(patch, kernel, sigmaX):
            calls.append((patch.shape, kernel, sigmaX))
            return np.broadcast_to(patch.mean(axis=(0, 1)), patch.shape).copy()

        blurred = blur_rgb_patches(
            patches,
            100,
            cv2=SimpleNamespace(GaussianBlur=gaussian_blur),
        )
        self.assertEqual(blurred.shape, (15, 32, 32, 3))
        self.assertLess(int(blurred[0, 16, 16, 0]), 255)
        self.assertEqual(len(calls), 15)
        self.assertTrue(all(call[1] == (31, 31) for call in calls))
        with self.assertRaises(DetectionError):
            blur_rgb_patches(
                patches[:14], 100, cv2=SimpleNamespace(GaussianBlur=gaussian_blur)
            )

    def test_upload_validation_and_ciphertext(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(service, "preflight_video_subprocess", return_value={"fps": 30, "frame_count": 300, "width": 1920, "height": 1080}):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mov", file=io.BytesIO(b"private-source"), headers={"content-type": "video/quicktime"})
                job = asyncio.run(service.create_job(db, self.storage, video, self.owner))
                self.assertNotIn(b"private-source", Path(job.original_path).read_bytes())
                self.assertEqual(list((self.storage.root / job.job_id / "work").glob("*")), [])
            runtime_commands = []

            def fail_runtime(command, _timeout):
                runtime_commands.append(command)
                raise DetectionError("runtime_incompatible")

            with patch.object(
                service.VideoPrivacyProcessor,
                "preflight",
                return_value={"width": 1920, "height": 1080, "frame_count": 300, "fps": 30.0},
            ) as source_preflight, patch.object(
                service.VideoPrivacyProcessor, "normalize_for_vsvig"
            ) as normalize, patch.object(service, "execute", side_effect=fail_runtime):
                with self.assertLogs(service.LOGGER, level="WARNING") as captured:
                    service.process_job(job.job_id)
            source_preflight.assert_called_once()
            normalize.assert_not_called()
            self.assertEqual(runtime_commands[0][3], runtime_commands[0][6])
            self.assertNotIn("normalized-input.mp4", runtime_commands[0][3])
            self.assertFalse((self.storage.root / job.job_id).exists())
            self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job.job_id}").json()["job"]["status"], "failed")
            failure_log = "\n".join(captured.output)
            self.assertIn("stage=pose-and-inference exception_type=DetectionError", failure_log)
            self.assertNotIn("runtime_incompatible", failure_log)
        response = self.alice.post(
            "/api/video-detection/jobs",
            content=b"x",
            headers={**self.headers, "Content-Type": "application/octet-stream", "X-Video-Format": "txt"},
        )
        self.assertEqual(response.status_code, 415)

    def test_upload_pose_failure_queues_privacy_review_without_running_inference(self):
        pose_readiness = {
            **POSE_READY,
            "ready": False,
            "frames_with_incomplete_pose": 1,
            "missing_landmarks": {"right ankle": 1},
        }
        with patch.object(service, "load_contract"), patch.object(
            service,
            "_preflight_uploaded_video",
            return_value={
                "width": 1920,
                "height": 1080,
                "fps": 25.0,
                "frame_count": 250,
                "pose_readiness": pose_readiness,
            },
        ):
            with patch.object(service, "process_job") as process_job:
                response = self.alice.post(
                    "/api/video-detection/jobs",
                    content=b"synthetic video bytes",
                    headers={
                        **self.headers,
                        "Content-Type": "application/octet-stream",
                        "X-Video-Format": "mp4",
                    },
                )

        self.assertEqual(response.status_code, 202, response.text)
        job = response.json()["job"]
        self.assertEqual(job["status"], "processing")
        self.assertEqual(job["current_stage"], "privacy-review")
        self.assertIn("opening five-second pose check", job["error"])
        self.assertIn("15 required landmarks", job["error"])
        process_job.assert_not_called()
        self.assertEqual(list(self.storage.root.glob("VID-*")), [])
        with Session(self.engine) as db:
            stored = db.exec(select(VideoDetectionJob)).one()
            self.assertEqual(stored.job_id, job["job_id"])
            self.assertIsNone(stored.original_path)

    def test_legacy_avi_upload_is_accepted_by_preflight(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service,
            "preflight_video_subprocess",
            return_value={"fps": 25, "frame_count": 250, "width": 1920, "height": 1080},
        ):
            with Session(self.engine) as db:
                video = UploadFile(
                    filename="recording.avi",
                    file=io.BytesIO(b"private-avi-source"),
                    headers=Headers({"content-type": "video/x-msvideo"}),
                )
                job = asyncio.run(service.create_job(db, self.storage, video, self.owner))

        self.assertEqual(job.fps, 25)
        self.assertEqual(job.duration_seconds, 10)

    def test_cancelled_upload_rolls_back_queued_job_and_storage(self):
        owner = self.owner
        if owner is None:
            self.fail("test owner was not created")
        video = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"), headers=Headers({"content-type": "video/mp4"}))
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            self.storage, "save_upload", new=AsyncMock(side_effect=asyncio.CancelledError),
        ):
            with Session(self.engine) as db:
                with self.assertRaises(asyncio.CancelledError):
                    asyncio.run(service.create_job(db, self.storage, video, self.owner))
                self.assertEqual(db.exec(select(VideoDetectionJob)).all(), [])
        self.assertEqual(list(self.storage.root.glob("VID-*")), [])
        self.assertEqual(
            self.alice.post(
                "/api/video-detection/jobs",
                content=b"x",
                headers={
                    "Origin": "https://wrong.invalid",
                    "Content-Type": "application/octet-stream",
                    "X-Video-Format": "mp4",
                },
            ).status_code,
            403,
        )

    def test_admission_cleanup_failure_persists_terminal_retry_record(self):
        owner = self.owner
        if owner is None:
            self.fail("test owner was not created")
        video = UploadFile(
            filename="patient.mp4",
            file=io.BytesIO(b"private-source"),
            headers=Headers({"content-type": "video/mp4"}),
        )
        encrypted = self.storage.root / "VID-CLEANUP" / "original" / "video.input.enc"
        encrypted.parent.mkdir(parents=True)
        encrypted.write_bytes(b"ciphertext")
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service.secrets, "token_hex", return_value="CLEANUP"
        ), patch.object(
            self.storage, "save_upload", new=AsyncMock(return_value=encrypted)
        ), patch.object(service, "_preflight_uploaded_video", side_effect=DetectionError("video_incompatible")), patch.object(
            self.storage, "delete_job", side_effect=OSError("cleanup unavailable")
        ):
            with Session(self.engine) as db:
                with self.assertRaises(DetectionError):
                    asyncio.run(service.create_job(db, self.storage, video, owner))
        with Session(self.engine) as db:
            saved = db.exec(
                select(VideoDetectionJob).where(VideoDetectionJob.job_id == "VID-CLEANUP")
            ).one()
            self.assertEqual(saved.status, "failed")
            self.assertEqual(saved.current_stage, "cleanup")
            self.assertEqual(saved.error_code, "processing_failed")
            self.assertEqual(saved.original_path, str(encrypted))

    def test_processing_cancellation_marks_job_interrupted_and_cleans_storage(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service, "preflight_video_subprocess", return_value={"fps": 30, "frame_count": 300, "width": 1920, "height": 1080},
        ):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"), headers=Headers({"content-type": "video/mp4"}))
                job = asyncio.run(service.create_job(db, self.storage, video, self.owner))

        with patch.object(
            service.VideoPrivacyProcessor,
            "preflight",
            return_value={"width": 1920, "height": 1080, "frame_count": 300, "fps": 30.0},
        ), patch.object(service, "execute", side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                service.process_job(job.job_id)
        with Session(self.engine) as db:
            saved = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job.job_id)).one()
            self.assertEqual(saved.status, "failed")
            self.assertEqual(saved.current_stage, "pose-and-inference")
            self.assertEqual(saved.error_code, "interrupted")
            self.assertIsNone(saved.original_path)
        self.assertFalse((self.storage.root / job.job_id).exists())

    def test_forced_expiry_removes_active_detection_job_media(self):
        job_id = self.seed()
        with Session(self.engine) as db:
            job = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            job.status = "processing"
            job.retention_expires_at = utc_now() - timedelta(seconds=1)
            db.add(job)
            db.commit()
            marker = self.storage.work_path(job_id, "inference.tmp")
            marker.write_bytes(b"private")
            service.expire_job(db, job, self.storage, force=True)
            self.assertEqual(job.status, "expired")
        self.assertFalse(marker.exists())
        self.assertFalse((self.storage.root / job_id).exists())

    def test_processing_success_encrypts_results_and_removes_plaintext(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service, "VSVIG_ALLOW_LETTERBOX_ADAPTATION", True,
        ), patch.object(
            service, "preflight_video_subprocess", return_value={"fps": 30, "frame_count": 300, "width": 640, "height": 480},
        ):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"), headers={"content-type": "video/mp4"})
                job = asyncio.run(
                    service.create_job(
                        db,
                        self.storage,
                        video,
                        self.owner,
                        blur_strength_percent=65,
                    )
                )

        commands = []

        def fake_execute(command, timeout):
            commands.append(command)
            if "backend.app.video_detection.runtime" in command:
                result = validate_predictions(
                    [{"start_time": 0, "end_time": 2, "raw_score": 0.8}],
                    10,
                    {"threshold": 0.5},
                )
                result.update(
                    {
                        "duration_seconds": 10.0,
                        "fps": 30.0,
                        "frame_count": 300,
                        "visualization": {
                            "available": True,
                            "media_type": "video/mp4",
                            "audio_included": False,
                            "privacy_method": "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
                            "face_blur_coverage": 1.0,
                            "full_frame_fallback_frames": 0,
                            "quality_flags": [],
                            "frame_count": 300,
                            "fps": 30,
                            "width": 1920,
                            "height": 1080,
                            "duration_seconds": 10,
                            "overlay": {"skeleton": True, "model_score": False, "event_markers": False},
                        },
                    }
                )
                Path(command[4]).write_text(json.dumps(result))
                Path(command[5]).write_bytes(b"review-video")
            else:
                Path(command[-1]).write_bytes(b"review-video")
            return subprocess.CompletedProcess(command, 0)

        with patch.object(service, "execute", side_effect=fake_execute), patch.object(
            service, "VSVIG_ALLOW_LETTERBOX_ADAPTATION", True,
        ), patch.object(
            service.VideoPrivacyProcessor,
            "preflight",
            return_value={"width": 640, "height": 480, "frame_count": 300, "fps": 30.0},
        ), patch.object(
            service.VideoPrivacyProcessor,
            "normalize_for_vsvig",
            return_value={"adaptation": "letterbox", "source_width": 640, "source_height": 480, "width": 1920, "height": 1080, "frame_count": 300, "fps": 30.0, "source_timestamp_offset_seconds": 1234.567, "padding_ltrb": [240, 0, 240, 0]},
        ) as normalize, patch.object(
            service, "validate_visualization_artifact"):
            service.process_job(job.job_id)

        with Session(self.engine) as db:
            saved = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job.job_id)).one()
            self.assertEqual(saved.status, "ready")
            self.assertEqual(saved.blur_strength_percent, 65)
            self.assertIsNone(saved.original_path)
            self.assertIsNone(saved.video_path)
            predictions_path = saved.predictions_path
            if predictions_path is None:
                self.fail("predictions artifact path was not stored")
            self.assertTrue(predictions_path.endswith(".enc"))
            visualization_path = saved.visualization_path
            if visualization_path is None:
                self.fail("redacted visualization artifact path was not stored")
            self.assertTrue(visualization_path.endswith(".enc"))
        runtime = next(command for command in commands if "backend.app.video_detection.runtime" in command)
        self.assertTrue(runtime[3].endswith("normalized-input.mp4"))
        self.assertEqual(len(runtime), 8)
        self.assertEqual(runtime[6], runtime[3])
        self.assertEqual(runtime[7], "65")
        private_predictions = self.storage.materialize_artifact(
            job.job_id, Path(predictions_path), "inspect-predictions.json"
        )
        try:
            stored_result = json.loads(private_predictions.read_text())
        finally:
            self.storage.delete_work_file(private_predictions)
        self.assertNotIn(
            "source_timestamp_offset_seconds", stored_result.get("privacy", {})
        )
        result = self.alice.get(f"/api/video-detection/jobs/{job.job_id}/predictions").json()
        self.assertNotIn("source_timestamp_offset_seconds", result.get("privacy", {}))
        self.assertEqual(result["privacy"]["method"], "tracked-face-blur-with-full-frame-fallback")
        self.assertTrue(normalize.call_args.kwargs["allow_letterbox_adaptation"])
        self.assertEqual(result["privacy"]["model_input_adaptation"], "letterbox")
        self.assertTrue(result["privacy"]["adaptation_experimental"])
        self.assertEqual(result["privacy"]["source_resolution"], [640, 480])
        self.assertEqual(result["privacy"]["model_resolution"], [1920, 1080])
        self.assertEqual(result["privacy"]["model_input_padding_ltrb"], [240, 0, 240, 0])
        self.assertEqual(
            result["privacy"]["pose_model_input"],
            "transient unblurred model frames; only pose coordinates and individually blurred RGB patches reach VSViG",
        )
        self.assertEqual(
            result["privacy"]["model_input"],
            "15 individually blurred RGB patches per sampled frame",
        )
        self.assertEqual(result["privacy"]["blur_strength_percent"], 65)
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job.job_id}").json()["job"]["blur_strength_percent"],
            65,
        )
        self.assertFalse(result["privacy"]["review_required"])
        self.assertEqual(result["privacy"]["quality_flags"], [])
        self.assertEqual(result["privacy"]["face_blur_coverage"], 1.0)
        self.assertEqual(result["timeline"][0]["score"], 0.8)
        self.assertEqual(result["events"][0]["peak_score"], 0.8)
        self.assertEqual(
            result["visualization"]["privacy_method"],
            "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
        )
        self.assertIn(
            "face-blurred, audio-free review video and encrypted predictions",
            result["privacy"]["audio_policy"],
        )
        playback = self.alice.get(
            f"/api/video-detection/jobs/{job.job_id}/visualization",
            headers={"Range": "bytes=0-8"},
        )
        self.assertEqual(playback.status_code, 206)
        retained_visualization = Path(visualization_path)
        self.assertTrue(retained_visualization.is_file())
        self.assertNotIn(b"review-video", retained_visualization.read_bytes())
        playback_cache = self.storage.root / job.job_id / "work" / "visualization-playback.mp4"
        self.assertTrue(playback_cache.is_file())
        self.assertEqual(list((self.storage.root / job.job_id / "work").glob("*.json")), [])

    def test_ready_detection_visualization_survives_startup_cleanup_until_expiry(self):
        job_id = self.seed(with_visualization=True)
        self.assertEqual(
            self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code,
            200,
        )
        playback = self.storage.root / job_id / "work" / "visualization-playback.mp4"
        self.assertTrue(playback.exists())
        with Session(self.engine) as db:
            seeded = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            encrypted_path = Path(seeded.visualization_path or "")
            self.assertTrue(encrypted_path.is_file())

        service.sweep(startup=True)

        self.assertFalse(playback.exists())
        with Session(self.engine) as db:
            saved = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            self.assertEqual(saved.visualization_path, str(encrypted_path))
        self.assertTrue(encrypted_path.exists())
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code, 200)
        self.assertEqual(self.bob.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code, 404)
        with TestClient(app) as anon:
            self.assertEqual(anon.get(f"/api/video-detection/jobs/{job_id}/visualization").status_code, 401)

    def test_processing_rejects_a_visualization_that_contains_audio(self):
        owner_id = self.owner
        if owner_id is None:
            self.fail("test owner was not created")
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service, "preflight_video_subprocess", return_value={"fps": 30, "frame_count": 300, "width": 1920, "height": 1080},
        ):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"), headers=Headers({"content-type": "video/mp4"}))
                job = asyncio.run(service.create_job(db, self.storage, video, owner_id))

        def fake_execute(command, timeout):
            result = validate_predictions(
                [{"start_time": 0, "end_time": 2, "raw_score": 0.8}],
                10,
                {"threshold": 0.5},
            )
            result["duration_seconds"] = 10.0
            result["fps"] = 30.0
            result["frame_count"] = 300
            result["visualization"] = {
                "available": True,
                "media_type": "video/mp4",
                "audio_included": True,
                "privacy_method": "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
                "overlay": {"skeleton": True, "model_score": False, "event_markers": False},
            }
            Path(command[4]).write_text(json.dumps(result))
            Path(command[5]).write_bytes(b"review-video")
            return subprocess.CompletedProcess(command, 0)

        with patch.object(service, "execute", side_effect=fake_execute), patch.object(
            service.VideoPrivacyProcessor,
            "preflight",
            return_value={"width": 1920, "height": 1080, "frame_count": 300, "fps": 30.0},
        ), patch.object(service, "validate_visualization_artifact"):
            service.process_job(job.job_id)

        with Session(self.engine) as db:
            saved = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job.job_id)).one()
            self.assertEqual(saved.status, "failed")
            self.assertEqual(saved.error_code, "visualization_failed")
            self.assertIsNone(saved.visualization_path)
        self.assertFalse((self.storage.root / job.job_id).exists())

    def test_contract_manifest_requires_an_external_hash(self):
        root = Path(self.temp.name)
        contract = root / "contract.json"
        contract.write_text('{"reviewed": true}')
        with patch.dict(os.environ, {"VSVIG_CONTRACT_SHA256": "0" * 64}):
            with self.assertRaisesRegex(DetectionError, "contract_unreviewed"):
                load_contract(root)

    def test_scores_preserve_support_and_merge_intervals(self):
        result = validate_predictions([
            {"start_time": 0, "end_time": 2, "raw_score": 0.6},
            {"start_time": 1, "end_time": 3, "raw_score": 0.7},
            {"start_time": 2, "end_time": 4, "raw_score": 0.1},
        ], 4, {"threshold": 0.5})
        self.assertEqual(result["intervals"], [{"start_time": 0, "end_time": 3}])
        self.assertFalse(result["recording_probability_available"])
        self.assertEqual(result["predictions"][0]["score_type"], "uncalibrated_model_score")
        evidence = {"method": "patch-occlusion", "patches": [
            {"patch_index": index, "score_change": index / 100} for index in range(15)
        ]}
        explained = validate_predictions(
            [{"start_time": 0, "end_time": 2, "raw_score": 0.6, "model_evidence": evidence}],
            4, {"threshold": 0.5},
        )
        self.assertEqual(explained["predictions"][0]["model_evidence"]["method"], "patch-occlusion")
        gradcam = {
            "method": "vsvig-graph-grad-cam",
            "target_class": "flagged",
            "note": "Synthetic graph Grad-CAM evidence.",
            "gradcam_samples": [
                {
                    "timestamp": index / 6,
                    "patches": [
                        {"patch_index": patch, "relevance": patch / 14}
                        for patch in range(15)
                    ],
                }
                for index in range(30)
            ],
        }
        explained_gradcam = validate_predictions(
            [
                {
                    "start_time": 0,
                    "end_time": 5,
                    "raw_score": 0.6,
                    "model_evidence": gradcam,
                }
            ],
            5,
            {"threshold": 0.5},
        )
        self.assertEqual(
            explained_gradcam["predictions"][0]["model_evidence"]["method"],
            "vsvig-graph-grad-cam",
        )
        self.assertEqual(
            len(
                explained_gradcam["predictions"][0]["model_evidence"][
                    "gradcam_samples"
                ]
            ),
            30,
        )
        gradcam["gradcam_samples"].pop()
        with self.assertRaises(DetectionError):
            validate_predictions(
                [
                    {
                        "start_time": 0,
                        "end_time": 5,
                        "raw_score": 0.6,
                        "model_evidence": gradcam,
                    }
                ],
                5,
                {"threshold": 0.5},
            )
        for value in (float("nan"), 1.01, -0.1):
            with self.assertRaises(DetectionError):
                validate_predictions([{"start_time": 0, "end_time": 2, "raw_score": value}], 4, {"threshold": 0.5})

    def test_contract_is_closed_by_default(self):
        root = Path(self.temp.name)
        with self.assertRaisesRegex(DetectionError, "assets_missing"):
            load_contract(root)
        (root / "contract.json").write_text('{"reviewed": false}')
        with self.assertRaisesRegex(DetectionError, "contract_unreviewed"):
            load_contract(root)
        (root / "contract.json").write_text('{"reviewed": true, "upstream_commit": "wrong"}')
        with patch.dict(os.environ, {"VSVIG_CONTRACT_SHA256": digest(root / "contract.json")}):
            with self.assertRaisesRegex(DetectionError, "contract_unreviewed"):
                load_contract(root)


if __name__ == "__main__":
    unittest.main()
