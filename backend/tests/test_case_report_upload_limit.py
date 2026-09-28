"""Bound concurrent buffered PDF uploads to protect backend memory."""

from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.core import config
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.eeg import AnalysisStatus, EEGSession
from backend.app.main import app
from backend.app.api.cases import _SOURCE_REPORT_UPLOAD_SLOTS


class CaseSourceReportUploadLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "test",
                "AUTH_MODE": "local-accounts",
                "MDS01_STORAGE_KEY": base64.b64encode(b"m" * 32).decode("ascii"),
            },
        )
        self.environment.start()
        self.storage = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(config, "STORAGE_DIR", Path(self.storage.name))
        self.storage_patch.start()
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
        self.client = TestClient(app)
        self.client.__enter__()
        origin = {"Origin": "http://localhost:3000"}
        registered = self.client.post(
            "/api/auth/register",
            json={"email": "upload-limit@example.test", "password": "synthetic test password"},
            headers=origin,
        )
        self.assertEqual(registered.status_code, 201)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "upload-limit@example.test", "password": "synthetic test password"},
            headers=origin,
        )
        self.assertEqual(login.status_code, 200)
        self.case_id = "CASE-ABCDEF12"
        with Session(self.engine) as db:
            owner = db.exec(select(User).where(User.email == "upload-limit@example.test")).one()
            assert owner.id is not None
            db.add(
                EEGSession(
                    session_id="SES-LIMIT-01",
                    owner_user_id=owner.id,
                    case_id=self.case_id,
                    status=AnalysisStatus.QUEUED,
                )
            )
            db.commit()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.engine.dispose()
        self.storage_patch.stop()
        self.storage.cleanup()
        self.environment.stop()

    def test_parallel_pdf_upload_is_rejected_before_reading_body(self) -> None:
        _SOURCE_REPORT_UPLOAD_SLOTS.acquire()
        try:
            response = self.client.put(
                f"/api/cases/{self.case_id}/report",
                content=b"%PDF-1.7\nSynthetic fixture\n%%EOF\n",
                headers={
                    "Origin": "http://localhost:3000",
                    "Content-Type": "application/pdf",
                },
            )
        finally:
            _SOURCE_REPORT_UPLOAD_SLOTS.release()

        self.assertEqual(response.status_code, 429)
        self.assertFalse((Path(self.storage.name) / "case-source-reports").exists())


if __name__ == "__main__":
    unittest.main()
