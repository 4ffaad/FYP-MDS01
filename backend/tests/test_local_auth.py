"""Tests for local accounts, server-side sessions, and record ownership."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.db import get_session
from backend.app.database.models.eeg import AnalysisStatus, EEGRecording, EEGSession, RecordingStatus, UploadDraft, utc_now
from backend.app.database.models.video import VideoPrivacyJob, VideoPrivacyProfile
from backend.app.main import app
from backend.app.database.models.auth import AuthSession
from backend.app.services.auth_service import (
    authenticate_local_user,
    ensure_demo_admin,
    register_user,
    token_hash,
)


@contextmanager
def local_accounts_environment():
    previous = {name: os.environ.get(name) for name in ("APP_ENV", "AUTH_MODE")}
    os.environ["APP_ENV"] = "test"
    os.environ["AUTH_MODE"] = "local-accounts"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class LocalAuthenticationTests(unittest.TestCase):
    """Exercise the HTTP boundary with two isolated accounts."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        def test_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = test_session
        self.environment = local_accounts_environment()
        self.environment.__enter__()

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        self.environment.__exit__(None, None, None)
        self.engine.dispose()

    def _client(self) -> TestClient:
        return TestClient(app)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"Origin": "http://localhost:3000"}

    def _register(self, client: TestClient, email: str) -> None:
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": "correct horse battery"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_eight_character_password_is_accepted(self) -> None:
        with Session(self.engine) as db:
            register_user(db, "eight@example.test", "12345678")
            with self.assertRaisesRegex(ValueError, "8 characters"):
                register_user(db, "seven@example.test", "1234567")

    def test_demo_admin_is_seeded_and_can_see_all_sessions(self) -> None:
        with Session(self.engine) as db, patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "AUTH_MODE": "local-accounts",
                "DEMO_ADMIN_ENABLED": "true",
                "DEMO_ADMIN_EMAIL": "admin@mds01.local",
                "DEMO_ADMIN_PASSWORD": "12345678",
            },
        ):
            admin = ensure_demo_admin(db)
            self.assertEqual(admin.email, "admin@mds01.local")
            self.assertEqual(admin.display_name, "admin")
            self.assertTrue(admin.is_admin)
            self.assertIs(ensure_demo_admin(db), admin)
            alice = register_user(db, "alice@example.test", "correct horse battery")
            bob = register_user(db, "bob@example.test", "correct horse battery")
            db.add_all(
                [
                    EEGSession(
                        session_id="SES-ALICE",
                        owner_user_id=alice.id,
                        status=AnalysisStatus.COMPLETED,
                    ),
                    EEGSession(
                        session_id="SES-BOB",
                        owner_user_id=bob.id,
                        status=AnalysisStatus.COMPLETED,
                    ),
                ]
            )
            db.commit()

        with self._client() as client:
            login = client.post(
                "/api/auth/login",
                json={"email": "admin@mds01.local", "password": "12345678"},
                headers=self._headers(),
            )
            self.assertEqual(login.status_code, 200, login.text)
            self.assertEqual(
                {item["session_id"] for item in client.get("/api/sessions").json()},
                {"SES-ALICE", "SES-BOB"},
            )

    def test_register_login_session_and_logout(self) -> None:
        with self._client() as client:
            self._register(client, "Alice@Example.test")
            self.assertEqual(client.get("/api/auth/session").json()["user"]["email"], "alice@example.test")
            cookie = client.cookies.get("mds01_session")
            self.assertIsNotNone(cookie)
            set_cookie = client.post(
                "/api/auth/login",
                json={"email": "alice@example.test", "password": "correct horse battery"},
                headers=self._headers(),
            ).headers["set-cookie"]
            self.assertIn("HttpOnly", set_cookie)
            self.assertIn("SameSite=lax", set_cookie)
            self.assertIn("Max-Age=28800", set_cookie)
            self.assertEqual(client.get("/api/sessions").status_code, 200)
            self.assertEqual(client.post("/api/auth/logout", headers=self._headers()).status_code, 204)
            self.assertEqual(client.get("/api/sessions").status_code, 401)

    def test_registration_and_login_errors_do_not_disclose_accounts(self) -> None:
        with self._client() as client:
            self._register(client, "alice@example.test")
            duplicate = client.post(
                "/api/auth/register",
                json={"email": "ALICE@example.test", "password": "correct horse battery"},
                headers=self._headers(),
            )
            self.assertEqual(duplicate.status_code, 409)
            weak = client.post(
                "/api/auth/register",
                json={"email": "weak@example.test", "password": "short"},
                headers=self._headers(),
            )
            self.assertEqual(weak.status_code, 422)
            wrong = client.post(
                "/api/auth/login",
                json={"email": "alice@example.test", "password": "wrong password"},
                headers=self._headers(),
            )
            self.assertEqual(wrong.status_code, 401)
            self.assertNotIn("alice@example.test", wrong.text)

    def test_state_changes_require_a_configured_origin(self) -> None:
        with self._client() as client:
            response = client.post(
                "/api/auth/register",
                json={"email": "alice@example.test", "password": "correct horse battery"},
            )
        self.assertEqual(response.status_code, 403)

    def test_expired_session_fails_closed(self) -> None:
        with Session(self.engine) as db:
            register_user(db, "alice@example.test", "correct horse battery")
            _, raw_token = authenticate_local_user(db, "alice@example.test", "correct horse battery")
            session = db.exec(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token))).first()
            assert session is not None
            session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.add(session)
            db.commit()
        with self._client() as client:
            client.cookies.set("mds01_session", raw_token)
            self.assertEqual(client.get("/api/sessions").status_code, 401)

    def test_users_only_see_owned_and_not_legacy_records(self) -> None:
        with Session(self.engine) as db:
            alice = register_user(db, "alice@example.test", "correct horse battery")
            bob = register_user(db, "bob@example.test", "correct horse battery")
            db.add_all([
                EEGSession(session_id="SES-ALICE", owner_user_id=alice.id, status=AnalysisStatus.COMPLETED),
                EEGSession(session_id="SES-BOB", owner_user_id=bob.id, status=AnalysisStatus.COMPLETED),
                EEGSession(session_id="SES-LEGACY", status=AnalysisStatus.COMPLETED),
                UploadDraft(
                    draft_id="DRAFT-ALICE",
                    owner_user_id=alice.id,
                    encrypted_path="",
                    expires_at=utc_now() + timedelta(hours=1),
                ),
                UploadDraft(
                    draft_id="DRAFT-BOB",
                    owner_user_id=bob.id,
                    encrypted_path="",
                    expires_at=utc_now() + timedelta(hours=1),
                ),
                VideoPrivacyJob(job_id="VID-ALICE", owner_user_id=alice.id, profile=VideoPrivacyProfile.FACE_REDACTED, display_label="Video upload 01"),
                VideoPrivacyJob(job_id="VID-BOB", owner_user_id=bob.id, profile=VideoPrivacyProfile.FACE_REDACTED, display_label="Video upload 01"),
            ])
            db.flush()
            sessions = {
                session.session_id: session
                for session in db.exec(select(EEGSession)).all()
            }
            db.add_all([
                EEGRecording(
                    record_id="REC-ALICE",
                    session_db_id=sessions["SES-ALICE"].id,
                    original_filename="",
                    status=RecordingStatus.PROCESSED,
                ),
                EEGRecording(
                    record_id="REC-BOB",
                    session_db_id=sessions["SES-BOB"].id,
                    original_filename="",
                    status=RecordingStatus.PROCESSED,
                ),
            ])
            db.commit()
        with self._client() as client:
            login = client.post(
                "/api/auth/login",
                json={"email": "alice@example.test", "password": "correct horse battery"},
                headers=self._headers(),
            )
            self.assertEqual(login.status_code, 200, login.text)
            self.assertEqual([item["session_id"] for item in client.get("/api/sessions").json()], ["SES-ALICE"])
            self.assertEqual(client.get("/api/sessions/SES-BOB").status_code, 404)
            self.assertEqual(client.get("/api/sessions/SES-LEGACY").status_code, 404)
            self.assertEqual([item["job_id"] for item in client.get("/api/video-privacy/jobs").json()["jobs"]], ["VID-ALICE"])
            self.assertEqual(client.get("/api/video-privacy/jobs/VID-BOB").status_code, 404)
            self.assertEqual(client.get("/api/uploads/drafts/DRAFT-ALICE").status_code, 200)
            self.assertEqual(client.get("/api/uploads/drafts/DRAFT-BOB").status_code, 404)
            self.assertEqual(client.get("/api/recordings/REC-ALICE").status_code, 200)
            self.assertEqual(client.get("/api/recordings/REC-BOB").status_code, 404)


if __name__ == "__main__":
    unittest.main()
