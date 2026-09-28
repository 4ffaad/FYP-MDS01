"""Synthetic API contract tests for owner-scoped case source reports."""

from __future__ import annotations

import base64
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.core import config
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.case_profile import CasePatientProfile
from backend.app.database.models.case_source_report import CaseSourceReport
from backend.app.database.models.eeg import AnalysisStatus, EEGSession
from backend.app.main import app
from backend.app.services import case_source_report_service
from backend.app.services.case_source_report_service import (
    CaseSourceReportCryptoError,
    CaseSourceReportStorageError,
    _decrypt_pdf,
    _read_artifact,
    save_case_source_report,
)


_SYNTHETIC_PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"


def _key_b64() -> str:
    return base64.b64encode(b"s" * 32).decode("ascii")


def _report_for_owner(db: Session, case_id: str, owner_user_id: int) -> CaseSourceReport | None:
    return db.exec(
        select(CaseSourceReport).where(
            CaseSourceReport.case_id == case_id,
            CaseSourceReport.owner_user_id == owner_user_id,
        )
    ).first()


class CaseSourceReportApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "test",
                "AUTH_MODE": "local-accounts",
                "MDS01_STORAGE_KEY": _key_b64(),
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
        self.owner = self._register("report-owner@example.test")
        assert self.owner.id is not None
        self.owner_id = self.owner.id
        self.case_id = "CASE-ABCD1234"
        with Session(self.engine) as db:
            db.add(
                EEGSession(
                    session_id="SES-REPORT-01",
                    owner_user_id=self.owner.id,
                    case_id=self.case_id,
                    status=AnalysisStatus.QUEUED,
                )
            )
            db.commit()
        self.headers = {
            "Origin": "http://localhost:3000",
            "Content-Type": "application/pdf",
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.engine.dispose()
        self.storage_patch.stop()
        self.storage.cleanup()
        self.environment.stop()

    def _register(self, email: str) -> User:
        origin = {"Origin": "http://localhost:3000"}
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "synthetic test password"},
            headers=origin,
        )
        self.assertEqual(response.status_code, 201)
        login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "synthetic test password"},
            headers=origin,
        )
        self.assertEqual(login.status_code, 200)
        with Session(self.engine) as db:
            user = db.exec(select(User).where(User.email == email)).one()
            db.expunge(user)
            return user

    def test_invalid_signature_and_wrong_media_type_are_rejected_safely(self) -> None:
        url = f"/api/cases/{self.case_id}/report"
        invalid = self.client.put(
            url,
            content=b"SYNTHETIC NOT A PDF",
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn("SYNTHETIC NOT A PDF", invalid.text)
        wrong_type = self.client.put(
            url,
            content=_SYNTHETIC_PDF,
            headers={
                "Origin": "http://localhost:3000",
                "Content-Type": "application/octet-stream",
            },
        )
        self.assertEqual(wrong_type.status_code, 415)
        self.assertFalse((Path(self.storage.name) / "case-source-reports").exists())

    def test_declared_oversize_body_is_rejected_before_storage(self) -> None:
        with patch("backend.app.api.cases.MAX_CASE_SOURCE_REPORT_BYTES", 8):
            response = self.client.put(
                f"/api/cases/{self.case_id}/report",
                content=_SYNTHETIC_PDF,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 413)
        self.assertFalse((Path(self.storage.name) / "case-source-reports").exists())

    def test_cross_owner_report_operations_are_not_found(self) -> None:
        url = f"/api/cases/{self.case_id}/report"
        saved = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)
        self.client.post(
            "/api/auth/logout",
            headers={"Origin": "http://localhost:3000"},
        )
        self._register("report-other-owner@example.test")
        origin = {"Origin": "http://localhost:3000"}

        loaded = self.client.get(url, headers=origin)
        replaced = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        deleted = self.client.delete(url, headers=origin)

        self.assertEqual(loaded.status_code, 404)
        self.assertEqual(replaced.status_code, 404)
        self.assertEqual(deleted.status_code, 404)
        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.owner_user_id, self.owner_id)

    def test_decrypted_pdf_size_is_bounded_and_errors_stay_generic(self) -> None:
        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)

        with patch(
            "backend.app.services.case_source_report_service.MAX_CASE_SOURCE_REPORT_BYTES",
            8,
        ):
            loaded = self.client.get(
                f"/api/cases/{self.case_id}/report",
                headers={"Origin": "http://localhost:3000"},
            )

        self.assertEqual(loaded.status_code, 503)
        self.assertNotIn("case-source-reports", loaded.text)
        self.assertNotIn(_SYNTHETIC_PDF.decode("latin-1"), loaded.text)

    def test_ciphertext_authentication_binds_owner_case_and_artifact(self) -> None:
        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)
        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None and row.artifact_id is not None
            artifact_id = row.artifact_id

        encrypted = _read_artifact(artifact_id)
        self.assertEqual(
            _decrypt_pdf(
                encrypted,
                owner_user_id=self.owner_id,
                case_id=self.case_id,
                artifact_id=artifact_id,
                version=1,
            ),
            _SYNTHETIC_PDF,
        )
        other_artifact_id = artifact_id[:-1] + ("0" if artifact_id[-1] != "0" else "1")
        for owner_id, case_id, candidate_artifact_id in (
            (self.owner_id + 1, self.case_id, artifact_id),
            (self.owner_id, self.case_id + "X", artifact_id),
            (self.owner_id, self.case_id, other_artifact_id),
        ):
            with self.subTest(owner_id=owner_id, case_id=case_id):
                with self.assertRaises(CaseSourceReportCryptoError):
                    _decrypt_pdf(
                        encrypted,
                        owner_user_id=owner_id,
                        case_id=case_id,
                        artifact_id=candidate_artifact_id,
                        version=1,
                    )

    def test_replacing_a_profile_keeps_the_case_report_attached(self) -> None:
        report_url = f"/api/cases/{self.case_id}/report"
        profile_url = f"/api/cases/{self.case_id}/patient-profile"
        saved = self.client.put(report_url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)
        for name in ("Synthetic Patient One", "Synthetic Patient Two"):
            profile = self.client.put(
                profile_url,
                json={
                    "name": name,
                    "hospital_id": "SYNTHETIC-001",
                    "review_confirmed": True,
                },
                headers={"Origin": "http://localhost:3000"},
            )
            self.assertEqual(profile.status_code, 200)

        loaded = self.client.get(report_url, headers={"Origin": "http://localhost:3000"})

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.content, _SYNTHETIC_PDF)
        self.assertEqual(
            len(list((Path(self.storage.name) / "case-source-reports").glob("*.enc"))),
            1,
        )

    def test_failed_replacement_preserves_the_previous_pdf(self) -> None:
        url = f"/api/cases/{self.case_id}/report"
        saved = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)
        replacement_pdf = b"%PDF-1.6\nSynthetic replacement report\n%%EOF\n"

        with patch(
            "backend.app.services.case_source_report_service.os.replace",
            side_effect=OSError("synthetic filesystem failure"),
        ):
            failed = self.client.put(url, content=replacement_pdf, headers=self.headers)

        self.assertEqual(failed.status_code, 503)
        loaded = self.client.get(url, headers={"Origin": "http://localhost:3000"})
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.content, _SYNTHETIC_PDF)
        private_root = Path(self.storage.name) / "case-source-reports"
        self.assertEqual(len(list(private_root.glob("*.enc"))), 1)
        self.assertEqual(len(list(private_root.glob(".*.tmp"))), 0)

        replaced = self.client.put(url, content=replacement_pdf, headers=self.headers)
        self.assertEqual(replaced.status_code, 204)
        loaded_replacement = self.client.get(
            url,
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(loaded_replacement.status_code, 200)
        self.assertEqual(loaded_replacement.content, replacement_pdf)
        self.assertEqual(len(list(private_root.glob("*.enc"))), 1)
        self.assertNotIn(replacement_pdf, next(private_root.glob("*.enc")).read_bytes())

    def test_delete_endpoint_removes_ciphertext_and_metadata(self) -> None:
        url = f"/api/cases/{self.case_id}/report"
        saved = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)

        deleted = self.client.delete(url, headers={"Origin": "http://localhost:3000"})

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            list((Path(self.storage.name) / "case-source-reports").glob("*.enc")),
            [],
        )
        with Session(self.engine) as db:
            self.assertIsNone(_report_for_owner(db, self.case_id, self.owner_id))

    def test_last_analysis_cleanup_failure_returns_a_generic_retryable_error(self) -> None:
        from backend.app.services.storage_service import SessionStorage

        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)
        with Session(self.engine) as db:
            session = db.exec(
                select(EEGSession).where(EEGSession.case_id == self.case_id)
            ).one()
            session.status = AnalysisStatus.COMPLETED
            db.add(session)
            db.commit()

        with (
            patch(
                "backend.app.api.sessions.SessionStorage",
                return_value=SessionStorage(
                    Path(self.storage.name) / "sessions",
                    storage_key=b"s" * 32,
                ),
            ),
            patch(
                "backend.app.services.case_source_report_service._remove_artifact",
                side_effect=CaseSourceReportStorageError("synthetic cleanup failure"),
            ),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            client.cookies.update(self.client.cookies)
            response = client.delete(
                "/api/sessions/SES-REPORT-01",
                headers={"Origin": "http://localhost:3000"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("synthetic cleanup failure", response.text)
        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNone(row.artifact_id)
            self.assertIsNotNone(row.cleanup_artifact_id)

    def test_last_analysis_commit_includes_profile_and_report_cleanup_intent(self) -> None:
        from backend.app.services import session_service
        from backend.app.services.session_service import delete_session
        from backend.app.services.storage_service import SessionStorage

        report_url = f"/api/cases/{self.case_id}/report"
        profile_url = f"/api/cases/{self.case_id}/patient-profile"
        saved = self.client.put(report_url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)
        profile = self.client.put(
            profile_url,
            json={
                "name": "Synthetic Patient",
                "hospital_id": "SYNTHETIC-001",
                "review_confirmed": True,
            },
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(profile.status_code, 200)
        with Session(self.engine) as db:
            session = db.exec(
                select(EEGSession).where(EEGSession.case_id == self.case_id)
            ).one()
            session.status = AnalysisStatus.COMPLETED
            db.add(session)
            db.commit()

        original_delete_session_data = session_service.delete_session_data

        def commit_then_interrupt(db, session) -> None:
            original_delete_session_data(db, session)
            raise RuntimeError("injected interruption after session commit")

        storage = SessionStorage(
            Path(self.storage.name) / "sessions",
            storage_key=b"s" * 32,
        )
        with (
            patch.object(
                session_service,
                "delete_session_data",
                side_effect=commit_then_interrupt,
            ),
            Session(self.engine) as db,
            self.assertRaisesRegex(RuntimeError, "after session commit"),
        ):
            session = db.exec(
                select(EEGSession).where(EEGSession.case_id == self.case_id)
            ).one()
            delete_session(db, storage, session)

        with Session(self.engine) as db:
            self.assertIsNone(db.exec(select(EEGSession)).first())
            self.assertIsNone(db.exec(select(CasePatientProfile)).first())
            report = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(report)
            assert report is not None
            self.assertIsNone(report.artifact_id)
            self.assertIsNotNone(report.cleanup_artifact_id)
            cleanup = case_source_report_service.cleanup_orphaned_case_source_reports
            cleanup(db)
            self.assertIsNone(_report_for_owner(db, self.case_id, self.owner_id))

        self.assertEqual(
            list((Path(self.storage.name) / "case-source-reports").glob("*.enc")),
            [],
        )

    def test_legacy_case_cleanup_waits_for_last_owner_attachment(self) -> None:
        from backend.app.services.session_service import delete_session
        from backend.app.services.storage_service import SessionStorage

        legacy_session_ids = (
            "SES-LEGACY-1-ABCD1234",
            "SES-LEGACY-2-ABCD1234",
        )
        with Session(self.engine) as db:
            baseline = db.exec(
                select(EEGSession).where(EEGSession.session_id == "SES-REPORT-01")
            ).one()
            db.delete(baseline)
            for session_id in legacy_session_ids:
                db.add(
                    EEGSession(
                        session_id=session_id,
                        owner_user_id=self.owner_id,
                        case_id=None,
                        status=AnalysisStatus.COMPLETED,
                    )
                )
            db.commit()

        report_saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(report_saved.status_code, 204)
        profile_saved = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile",
            json={
                "name": "Synthetic Legacy Patient",
                "hospital_id": "SYNTHETIC-LEGACY-01",
                "review_confirmed": True,
            },
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(profile_saved.status_code, 200)

        storage = SessionStorage(
            Path(self.storage.name) / "sessions",
            storage_key=b"s" * 32,
        )
        for index, session_id in enumerate(legacy_session_ids):
            with Session(self.engine) as db:
                session = db.exec(
                    select(EEGSession).where(EEGSession.session_id == session_id)
                ).one()
                delete_session(db, storage, session)

            with Session(self.engine) as db:
                profile = db.exec(select(CasePatientProfile)).first()
                report = _report_for_owner(db, self.case_id, self.owner_id)
                if index == 0:
                    self.assertIsNotNone(profile)
                    self.assertIsNotNone(report)
                    assert report is not None
                    self.assertIsNotNone(report.artifact_id)
                else:
                    self.assertIsNone(profile)
                    self.assertIsNone(report)

    def test_legacy_case_id_collision_isolated_for_two_owners(self) -> None:
        from backend.app.services.case_profile_service import (
            delete_patient_profile,
            load_patient_profile,
            save_patient_profile,
        )
        from backend.app.services.case_source_report_service import load_case_source_report

        owner_one_pdf = b"%PDF-1.7\nSynthetic owner one\n%%EOF\n"
        owner_two_pdf = b"%PDF-1.7\nSynthetic owner two\n%%EOF\n"
        with Session(self.engine) as db:
            owner_two = User(
                public_id="USR-LEGACY-COLLISION-2",
                email="legacy-collision-two@example.test",
                password_hash="synthetic-only",
            )
            db.add(owner_two)
            db.commit()
            db.refresh(owner_two)
            assert owner_two.id is not None
            db.add_all(
                [
                    EEGSession(
                        session_id="SES-LEGACY-OWNER-1-ABCD1234",
                        owner_user_id=self.owner_id,
                        case_id=None,
                    ),
                    EEGSession(
                        session_id="SES-LEGACY-OWNER-2-ABCD1234",
                        owner_user_id=owner_two.id,
                        case_id=None,
                    ),
                ]
            )
            db.commit()

            save_patient_profile(
                db,
                case_id=self.case_id,
                owner_user_id=self.owner_id,
                name="Synthetic Owner One",
                hospital_id="SYNTHETIC-OWNER-1",
            )
            save_patient_profile(
                db,
                case_id=self.case_id,
                owner_user_id=owner_two.id,
                name="Synthetic Owner Two",
                hospital_id="SYNTHETIC-OWNER-2",
            )
            save_case_source_report(
                db,
                case_id=self.case_id,
                owner_user_id=self.owner_id,
                pdf_bytes=owner_one_pdf,
            )
            save_case_source_report(
                db,
                case_id=self.case_id,
                owner_user_id=owner_two.id,
                pdf_bytes=owner_two_pdf,
            )

            owner_one_profile = load_patient_profile(
                db,
                case_id=self.case_id,
                owner_user_id=self.owner_id,
            )
            owner_two_profile = load_patient_profile(
                db,
                case_id=self.case_id,
                owner_user_id=owner_two.id,
            )
            self.assertIsNotNone(owner_one_profile)
            self.assertIsNotNone(owner_two_profile)
            assert owner_one_profile is not None and owner_two_profile is not None
            self.assertEqual(owner_one_profile[0]["name"], "Synthetic Owner One")
            self.assertEqual(owner_two_profile[0]["name"], "Synthetic Owner Two")
            self.assertEqual(
                load_case_source_report(
                    db,
                    case_id=self.case_id,
                    owner_user_id=self.owner_id,
                ),
                owner_one_pdf,
            )
            self.assertEqual(
                load_case_source_report(
                    db,
                    case_id=self.case_id,
                    owner_user_id=owner_two.id,
                ),
                owner_two_pdf,
            )

            delete_patient_profile(db, case_id=self.case_id, owner_user_id=self.owner_id)
            self.assertIsNone(
                load_patient_profile(db, case_id=self.case_id, owner_user_id=self.owner_id)
            )
            self.assertIsNone(
                load_case_source_report(db, case_id=self.case_id, owner_user_id=self.owner_id)
            )
            owner_two_profile = load_patient_profile(
                db,
                case_id=self.case_id,
                owner_user_id=owner_two.id,
            )
            self.assertIsNotNone(owner_two_profile)
            assert owner_two_profile is not None
            self.assertEqual(owner_two_profile[0]["name"], "Synthetic Owner Two")
            self.assertEqual(
                load_case_source_report(db, case_id=self.case_id, owner_user_id=owner_two.id),
                owner_two_pdf,
            )
            delete_patient_profile(db, case_id=self.case_id, owner_user_id=owner_two.id)
            self.assertIsNone(
                load_patient_profile(db, case_id=self.case_id, owner_user_id=owner_two.id)
            )
            self.assertIsNone(
                load_case_source_report(db, case_id=self.case_id, owner_user_id=owner_two.id)
            )

    def test_deleting_the_last_analysis_removes_the_case_report(self) -> None:
        from backend.app.services.session_service import delete_session
        from backend.app.services.storage_service import SessionStorage

        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)
        with Session(self.engine) as db:
            session = db.exec(
                select(EEGSession).where(EEGSession.case_id == self.case_id)
            ).one()
            session.status = AnalysisStatus.COMPLETED
            db.add(session)
            db.commit()
            storage = SessionStorage(
                Path(self.storage.name) / "sessions",
                storage_key=b"s" * 32,
            )
            delete_session(db, storage, session)

        private_root = Path(self.storage.name) / "case-source-reports"
        self.assertEqual(list(private_root.glob("*.enc")), [])
        with Session(self.engine) as db:
            self.assertIsNone(_report_for_owner(db, self.case_id, self.owner_id))

    def test_cleanup_sweep_retries_report_delete_tombstones(self) -> None:
        url = f"/api/cases/{self.case_id}/report"
        saved = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)

        with patch(
            "backend.app.services.case_source_report_service._remove_artifact",
            side_effect=CaseSourceReportStorageError("synthetic cleanup failure"),
        ):
            failed_delete = self.client.delete(
                url,
                headers={"Origin": "http://localhost:3000"},
            )
        self.assertEqual(failed_delete.status_code, 503)

        with Session(self.engine) as db:
            cleanup = getattr(
                case_source_report_service,
                "cleanup_orphaned_case_source_reports",
                None,
            )
            self.assertTrue(callable(cleanup))
            assert callable(cleanup)
            cleanup(db)
            self.assertIsNone(_report_for_owner(db, self.case_id, self.owner_id))

        private_root = Path(self.storage.name) / "case-source-reports"
        self.assertEqual(list(private_root.glob("*.enc")), [])

    def test_cleanup_sweep_removes_only_old_unreferenced_report_files(self) -> None:
        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)
        private_root = Path(self.storage.name) / "case-source-reports"
        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None and row.artifact_id is not None
            active_path = private_root / f"{row.artifact_id}.enc"

            cleanup = getattr(
                case_source_report_service,
                "cleanup_orphaned_case_source_reports",
                None,
            )
            self.assertTrue(callable(cleanup), "report cleanup sweep is missing")

            orphan_id = "f" * 32 if row.artifact_id != "f" * 32 else "e" * 32
            fresh_orphan_id = "d" * 32
            orphan_path = private_root / f"{orphan_id}.enc"
            fresh_orphan_path = private_root / f"{fresh_orphan_id}.enc"
            stale_temp_path = private_root / ("." + "c" * 32 + ".tmp")
            for path in (orphan_path, fresh_orphan_path, stale_temp_path):
                path.write_bytes(b"synthetic encrypted fixture")
            stale_time = time.time() - 7200
            os.utime(orphan_path, (stale_time, stale_time))
            os.utime(stale_temp_path, (stale_time, stale_time))

            cleanup(db, older_than_seconds=3600)

        self.assertTrue(active_path.exists())
        self.assertFalse(orphan_path.exists())
        self.assertFalse(stale_temp_path.exists())
        self.assertTrue(fresh_orphan_path.exists())

    def test_sql_keeps_only_opaque_metadata_and_storage_is_ciphertext(self) -> None:
        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)

        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.owner_user_id, self.owner.id)
            self.assertEqual(row.crypto_version, 1)
            self.assertRegex(row.artifact_id or "", r"^[a-f0-9]{32}$")
            self.assertNotIn("/", row.artifact_id or "")

        private_root = Path(self.storage.name) / "case-source-reports"
        stored_files = list(private_root.glob("*.enc"))
        self.assertEqual(len(stored_files), 1)
        self.assertNotIn(_SYNTHETIC_PDF, stored_files[0].read_bytes())
        self.assertEqual(os.stat(private_root).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(stored_files[0]).st_mode & 0o777, 0o600)

    def test_commit_acknowledgement_loss_keeps_the_committed_pdf(self) -> None:
        with Session(self.engine) as db:
            original_commit = db.commit

            def commit_then_lose_acknowledgement() -> None:
                original_commit()
                raise RuntimeError("synthetic commit acknowledgement loss")

            with patch.object(db, "commit", side_effect=commit_then_lose_acknowledgement):
                save_case_source_report(
                    db,
                    case_id=self.case_id,
                    owner_user_id=self.owner_id,
                    pdf_bytes=_SYNTHETIC_PDF,
                )

        loaded = self.client.get(
            f"/api/cases/{self.case_id}/report",
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.content, _SYNTHETIC_PDF)
        self.assertEqual(
            len(list((Path(self.storage.name) / "case-source-reports").glob("*.enc"))),
            1,
        )

    def test_new_report_file_is_removed_if_metadata_commit_fails(self) -> None:
        with Session(self.engine) as db:
            with patch.object(db, "commit", side_effect=RuntimeError("synthetic commit failure")):
                with self.assertRaises(CaseSourceReportStorageError):
                    save_case_source_report(
                        db,
                        case_id=self.case_id,
                        owner_user_id=self.owner_id,
                        pdf_bytes=_SYNTHETIC_PDF,
                    )

        private_root = Path(self.storage.name) / "case-source-reports"
        self.assertEqual(list(private_root.iterdir()), [])
        with Session(self.engine) as db:
            self.assertIsNone(_report_for_owner(db, self.case_id, self.owner_id))

    def test_profile_delete_reports_generic_cleanup_failure(self) -> None:
        saved = self.client.put(
            f"/api/cases/{self.case_id}/report",
            content=_SYNTHETIC_PDF,
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 204)

        with (
            patch(
                "backend.app.services.case_source_report_service._remove_artifact",
                side_effect=CaseSourceReportStorageError("synthetic cleanup failure"),
            ),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            client.cookies.update(self.client.cookies)
            response = client.delete(
                f"/api/cases/{self.case_id}/patient-profile",
                headers={"Origin": "http://localhost:3000"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("synthetic cleanup failure", response.text)
        with Session(self.engine) as db:
            row = _report_for_owner(db, self.case_id, self.owner_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNone(row.artifact_id)
            self.assertIsNotNone(row.cleanup_artifact_id)

    def test_deleting_patient_profile_also_removes_the_case_report(self) -> None:
        report_url = f"/api/cases/{self.case_id}/report"
        profile_url = f"/api/cases/{self.case_id}/patient-profile"
        saved = self.client.put(report_url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204)
        profile = self.client.put(
            profile_url,
            json={
                "name": "Synthetic Patient",
                "hospital_id": "SYNTHETIC-001",
                "review_confirmed": True,
            },
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(profile.status_code, 200)

        deleted = self.client.delete(
            profile_url,
            headers={"Origin": "http://localhost:3000"},
        )

        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(
            report_url,
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(missing.status_code, 404)
        report_files = list((Path(self.storage.name) / "case-source-reports").glob("*.enc"))
        self.assertEqual(report_files, [])

    def test_owner_can_put_and_get_an_inline_uncached_pdf(self) -> None:
        url = f"/api/cases/{self.case_id}/report"

        saved = self.client.put(url, content=_SYNTHETIC_PDF, headers=self.headers)
        self.assertEqual(saved.status_code, 204, saved.text)

        loaded = self.client.get(url, headers={"Origin": "http://localhost:3000"})
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(loaded.content, _SYNTHETIC_PDF)
        self.assertEqual(loaded.headers["content-type"], "application/pdf")
        self.assertIn("inline", loaded.headers["content-disposition"])
        self.assertIn("no-store", loaded.headers["cache-control"])


if __name__ == "__main__":
    unittest.main()
