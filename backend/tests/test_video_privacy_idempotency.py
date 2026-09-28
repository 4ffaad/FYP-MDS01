"""Authenticated video-privacy retries do not duplicate jobs."""

from __future__ import annotations

import asyncio
import os
import hashlib
from pathlib import Path
import tempfile
import typing
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from backend.app.api.video_privacy import _drain_upload
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.video import VideoPrivacyJob
from backend.app.main import app
from backend.app.services.video_storage_service import VideoStorage


class VideoPrivacyIdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        def session_dependency():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_session] = session_dependency
        self.addCleanup(app.dependency_overrides.pop, get_session)
        self.storage = VideoStorage(
            Path(self.temp.name) / "sessions",
            storage_key=os.urandom(32),
        )
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.auth_environment = patch.dict(
            os.environ,
            {"APP_ENV": "test", "AUTH_MODE": "local-accounts"},
            clear=False,
        )
        self.auth_environment.start()
        self.addCleanup(self.auth_environment.stop)

    def _register(self, suffix: str) -> int:
        email = f"privacy-idempotency-{suffix}@example.test"
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": os.urandom(20).hex()},
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        with Session(self.engine) as db:
            owner_id = db.exec(select(User).where(User.email == email)).one().id
        assert owner_id is not None
        return owner_id

    def test_idempotent_replay_drain_enforces_exact_video_upload_limit(self) -> None:
        class SyntheticUpload:
            def __init__(self) -> None:
                self.chunks = iter((b"ab", b"cd", b""))

            async def read(self, _size: int) -> bytes:
                return next(self.chunks)

        with patch("backend.app.api.video_privacy.MAX_VIDEO_UPLOAD_BYTES", 3, create=True):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(typing.cast(typing.Any, _drain_upload)(SyntheticUpload()))
        self.assertEqual(raised.exception.status_code, 413)

    def test_http_idempotent_replay_enforces_exact_limit_after_middleware_cap(self) -> None:
        self._register("replay-limit")
        headers = {
            "Origin": "http://localhost:3000",
            "Content-Type": "application/octet-stream",
            "X-Video-Format": "mp4",
            "X-Video-Profile": "face-redacted-pose-preview",
            "Idempotency-Key": "replay-limit-content-key",
        }
        with (
            patch("backend.app.api.video_privacy.VideoStorage", return_value=self.storage),
            patch("backend.app.services.video_privacy_service.VideoStorage", return_value=self.storage),
            patch(
                "backend.app.services.video_privacy_service.preflight_video_subprocess",
                return_value={"fps": 24.0, "width": 640, "height": 360, "frame_count": 48},
            ),
            patch("backend.app.api.video_privacy.process_video_privacy_job"),
            patch("backend.app.api.video_privacy.MAX_VIDEO_UPLOAD_BYTES", 3),
            patch("backend.app.core.middleware.MAX_VIDEO_UPLOAD_BYTES", 10),
        ):
            first = self.client.post("/api/video-privacy/jobs", content=b"abc", headers=headers)
            self.assertEqual(first.status_code, 202, first.text)
            replay = self.client.post(
                "/api/video-privacy/jobs",
                content=iter((b"ab", b"cd")),
                headers=headers,
            )

        self.assertNotIn("content-length", replay.request.headers)
        self.assertEqual(replay.status_code, 413, replay.text)

    def test_reusing_idempotency_key_for_different_bytes_returns_conflict(self) -> None:
        self._register("different-bytes")
        headers = {
            "Origin": "http://localhost:3000",
            "Content-Type": "application/octet-stream",
            "X-Video-Format": "mp4",
            "X-Video-Profile": "face-redacted-pose-preview",
            "Idempotency-Key": "different-content-key-12345",
        }
        with (
            patch("backend.app.api.video_privacy.VideoStorage", return_value=self.storage),
            patch("backend.app.services.video_privacy_service.VideoStorage", return_value=self.storage),
            patch(
                "backend.app.services.video_privacy_service.preflight_video_subprocess",
                return_value={"fps": 24.0, "width": 640, "height": 360, "frame_count": 48},
            ),
            patch("backend.app.api.video_privacy.process_video_privacy_job"),
        ):
            first = self.client.post("/api/video-privacy/jobs", content=b"synthetic-first-bytes", headers=headers)
            self.assertEqual(first.status_code, 202, first.text)
            replay = self.client.post("/api/video-privacy/jobs", content=b"synthetic-different-bytes", headers=headers)

        self.assertEqual(replay.status_code, 409, replay.text)
        with Session(self.engine) as db:
            jobs = db.exec(select(VideoPrivacyJob)).all()
            self.assertEqual(len(jobs), 1)
            self.assertNotIn("content_fingerprint", replay.json()["job"] if "job" in replay.json() else {})
            self.assertNotIn("video_fingerprint", replay.text)

    def test_retry_returns_the_existing_owner_job_without_reencrypting(self) -> None:
        owner_id = self._register("owner")
        idempotency_key = "9f0ee62a-5ded-4a60-9871-6780f75f044a"
        payload = b"synthetic-video-upload"
        headers = {
            "Origin": "http://localhost:3000",
            "Content-Type": "application/octet-stream",
            "X-Video-Format": "mp4",
            "X-Video-Profile": "face-redacted-pose-preview",
            "Idempotency-Key": idempotency_key,
        }

        with (
            patch("backend.app.api.video_privacy.VideoStorage", return_value=self.storage),
            patch("backend.app.services.video_privacy_service.VideoStorage", return_value=self.storage),
            patch(
                "backend.app.services.video_privacy_service.preflight_video_subprocess",
                return_value={"fps": 24.0, "width": 640, "height": 360, "frame_count": 48},
            ),
            patch("backend.app.api.video_privacy.process_video_privacy_job"),
        ):
            first = self.client.post(
                "/api/video-privacy/jobs",
                content=payload,
                headers=headers,
            )
            self.assertEqual(first.status_code, 202, first.text)
            first_job_id = first.json()["job"]["job_id"]

            replay = self.client.post(
                "/api/video-privacy/jobs",
                content=payload,
                headers=headers,
            )

        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertEqual(replay.json()["job"]["job_id"], first_job_id)
        self.assertNotIn("idempotency_key", replay.json()["job"])
        self.assertNotIn("content_fingerprint", replay.text)
        with Session(self.engine) as db:
            jobs = db.exec(select(VideoPrivacyJob)).all()
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].owner_user_id, owner_id)
            self.assertEqual(
                jobs[0].idempotency_key_hash,
                hashlib.sha256(idempotency_key.encode("ascii")).hexdigest(),
            )
            self.assertEqual(
                jobs[0].content_fingerprint,
                hashlib.sha256(payload).hexdigest(),
            )
            self.assertNotIn(hashlib.sha256(payload).hexdigest(), first.text)
            encrypted_path = Path(jobs[0].original_path or "")
            self.assertTrue(encrypted_path.is_file())
            self.assertNotIn(payload, encrypted_path.read_bytes())
