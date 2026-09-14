"""Video-only contract, ownership, ciphertext, range playback, and cleanup checks."""

import asyncio
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from backend.app.database.db import get_session
from backend.app.database.models.video import utc_now
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.main import app
from backend.app.services import video_detection_service as service
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_detection.contract import DetectionError, digest, load_contract, validate_predictions
from backend.app.video_privacy.processor import VideoProcessingResult


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

    def seed(self, status="ready"):
        with Session(self.engine) as db:
            job = VideoDetectionJob(owner_user_id=self.owner, job_id="VID-" + os.urandom(16).hex(), status=status,
                                    duration_seconds=10, fps=30, retention_expires_at=utc_now() + timedelta(hours=1))
            path = self.storage.work_path(job.job_id, "review.mp4")
            path.write_bytes(b"synthetic-public-test-video")
            job.video_path = str(self.storage.store_artifact(job.job_id, path, "review.mp4"))
            results = self.storage.work_path(job.job_id, "predictions.json")
            results.write_text(json.dumps(validate_predictions([
                {"start_time": 0, "end_time": 2, "raw_score": 0.8},
            ], 10, {"threshold": 0.5})))
            job.predictions_path = str(self.storage.store_artifact(job.job_id, results, "predictions.json"))
            db.add(job); db.commit(); db.refresh(job)
            return job.job_id

    def test_auth_ownership_and_no_private_metadata(self):
        job_id = self.seed()
        for suffix in ("", "/predictions", "/video"):
            self.assertEqual(self.bob.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 404)
            with TestClient(app) as anon:
                self.assertEqual(anon.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 401)
        self.assertEqual(self.bob.get("/api/video-detection/jobs").json(), {"jobs": []})
        response = self.alice.get(f"/api/video-detection/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("path", response.text)
        self.assertNotIn(self.temp.name, response.text)

    def test_range_playback_is_private_and_plaintext_removed(self):
        job_id = self.seed()
        response = self.alice.get(f"/api/video-detection/jobs/{job_id}/video", headers={"Range": "bytes=0-8"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"synthetic")
        self.assertIn("no-store", response.headers["cache-control"])
        self.assertEqual(list((self.storage.root / job_id / "work").glob("*")), [])
        response = self.alice.get(f"/api/video-detection/jobs/{job_id}/video", headers={"Range": "bytes=900-999"})
        self.assertEqual(response.status_code, 416)
        self.assertEqual(list((self.storage.root / job_id / "work").glob("*")), [])
        ciphertext = (self.storage.root / job_id / "retained/review.mp4.enc").read_bytes()
        self.assertNotIn(b"synthetic-public-test-video", ciphertext)

    def test_expiry_sweep_removes_video_and_predictions_without_a_visit(self):
        job_id = self.seed()
        with Session(self.engine) as db:
            job = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)).one()
            job.retention_expires_at = utc_now() - timedelta(seconds=1)
            db.add(job); db.commit()
        service.sweep()
        self.assertFalse((self.storage.root / job_id).exists())
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/video").status_code, 409)
        self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job_id}/predictions").status_code, 409)

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
                response = self.alice.post("/api/video-detection/jobs", files={"video": ("private-name.mp4", b"test", "video/mp4")}, headers=self.headers)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private-name", response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(VideoDetectionJob)).all(), [])

    def test_upload_validation_and_ciphertext(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(service.VideoPrivacyProcessor, "preflight", return_value={"fps": 30, "frame_count": 300}):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mov", file=io.BytesIO(b"private-source"), headers={"content-type": "video/quicktime"})
                job = asyncio.run(service.create_job(db, self.storage, video, self.owner))
                self.assertNotIn(b"private-source", Path(job.original_path).read_bytes())
                self.assertEqual(list((self.storage.root / job.job_id / "work").glob("*")), [])
            with patch.object(service, "execute", side_effect=DetectionError("runtime_incompatible")):
                service.process_job(job.job_id)
            self.assertFalse((self.storage.root / job.job_id).exists())
            self.assertEqual(self.alice.get(f"/api/video-detection/jobs/{job.job_id}").json()["job"]["status"], "failed")
        response = self.alice.post("/api/video-detection/jobs", files={"video": ("secret.txt", b"x", "text/plain")}, headers=self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.alice.post("/api/video-detection/jobs", files={"video": ("a.mp4", b"x", "video/mp4")}, headers={"Origin": "https://wrong.invalid"}).status_code, 403)

    def test_processing_success_encrypts_results_and_removes_plaintext(self):
        with patch.object(service, "load_contract", return_value=(Path(self.temp.name), {})), patch.object(
            service.VideoPrivacyProcessor, "preflight", return_value={"fps": 30, "frame_count": 300},
        ):
            with Session(self.engine) as db:
                video = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"), headers={"content-type": "video/mp4"})
                job = asyncio.run(service.create_job(db, self.storage, video, self.owner))

        commands = []

        def fake_execute(command, timeout):
            commands.append(command)
            target = Path(command[-1])
            if "backend.app.video_detection.runtime" in command:
                target.write_text(json.dumps({"predictions": [{"start_time": 0, "end_time": 2, "raw_score": 0.8}]}))
            else:
                target.write_bytes(b"review-video")
            return subprocess.CompletedProcess(command, 0)

        protected = VideoProcessingResult(
            duration_seconds=10, fps=30, width=1920, height=1080, frame_count=300,
            detected_frames=270, quality_flags=["intermittent_detection"], usable=True, needs_review=True,
        )
        with patch.object(service, "execute", side_effect=fake_execute), patch.object(
            service.VideoPrivacyProcessor, "process", return_value=protected,
        ):
            service.process_job(job.job_id)

        with Session(self.engine) as db:
            saved = db.exec(select(VideoDetectionJob).where(VideoDetectionJob.job_id == job.job_id)).one()
            self.assertEqual(saved.status, "ready")
            self.assertIsNone(saved.original_path)
            self.assertTrue(saved.video_path.endswith(".enc"))
            self.assertTrue(saved.predictions_path.endswith(".enc"))
        runtime = next(command for command in commands if "backend.app.video_detection.runtime" in command)
        self.assertTrue(runtime[-2].endswith("model-input.mp4"))
        result = self.alice.get(f"/api/video-detection/jobs/{job.job_id}/predictions").json()
        self.assertEqual(result["privacy"]["method"], "face-redaction")
        self.assertTrue(result["privacy"]["review_required"])
        self.assertEqual(list((self.storage.root / job.job_id / "work").glob("*")), [])

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
            with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                load_contract(root)


if __name__ == "__main__":
    unittest.main()
