"""Profile/report deletion remains recoverable across interrupted cleanup."""

from __future__ import annotations

import base64
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.core import config
from backend.app.database.models.auth import User
from backend.app.database.models.case_profile import CasePatientProfile
from backend.app.database.models.case_source_report import CaseSourceReport
from backend.app.services.case_profile_service import (
    CRYPTO_VERSION,
    delete_patient_profile,
    encrypt_profile,
)
from backend.app.services.case_source_report_service import (
    cleanup_orphaned_case_source_reports,
    save_case_source_report,
)


class OrphanedCasePrivacyCleanupTests(unittest.TestCase):
    def test_interrupted_cleanup_leaves_report_tombstone_for_recovery(self) -> None:
        environment = patch.dict(
            os.environ,
            {"MDS01_STORAGE_KEY": base64.b64encode(b"s" * 32).decode("ascii")},
        )
        storage = tempfile.TemporaryDirectory()
        storage_patch = patch.object(config, "STORAGE_DIR", Path(storage.name))
        environment.start()
        storage_patch.start()
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        case_id = "CASE-ABCD1234"
        report_pdf = b"%PDF-1.7\nSynthetic report\n%%EOF\n"

        try:
            with Session(engine) as db:
                user = User(
                    public_id="USR-SYNTHETIC",
                    email="orphan-cleanup@example.test",
                    password_hash="synthetic-hash",
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                assert user.id is not None
                owner_id = user.id
                nonce, ciphertext = encrypt_profile(
                    owner_id,
                    case_id,
                    {
                        "name": "Synthetic Patient",
                        "hospital_id": "SYNTHETIC-01",
                        "age": "",
                        "findings": "",
                    },
                )
                db.add(
                    CasePatientProfile(
                        case_id=case_id,
                        owner_user_id=owner_id,
                        identity_nonce=nonce,
                        identity_ciphertext=ciphertext,
                        crypto_version=CRYPTO_VERSION,
                        reviewed_by_user_id=owner_id,
                        reviewed_at=datetime.now(timezone.utc),
                    )
                )
                db.commit()
                save_case_source_report(
                    db,
                    case_id=case_id,
                    owner_user_id=owner_id,
                    pdf_bytes=report_pdf,
                )

                with patch(
                    "backend.app.services.case_profile_service.delete_case_source_report",
                    side_effect=RuntimeError("injected interruption before report cleanup"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "injected interruption"):
                        delete_patient_profile(
                            db,
                            case_id=case_id,
                            owner_user_id=owner_id,
                        )

                self.assertIsNone(db.exec(select(CasePatientProfile)).first())
                report = db.exec(
                    select(CaseSourceReport).where(
                        CaseSourceReport.case_id == case_id,
                        CaseSourceReport.owner_user_id == owner_id,
                    )
                ).first()
                self.assertIsNotNone(report)
                assert report is not None
                self.assertIsNone(report.artifact_id)
                self.assertIsNotNone(report.cleanup_artifact_id)
                cleanup_orphaned_case_source_reports(db)

                self.assertIsNone(
                    db.exec(
                        select(CaseSourceReport).where(
                            CaseSourceReport.case_id == case_id,
                            CaseSourceReport.owner_user_id == owner_id,
                        )
                    ).first()
                )
                self.assertIsNone(db.exec(select(CasePatientProfile)).first())
                encrypted_files = list(
                    (Path(storage.name) / "case-source-reports").glob("*.enc")
                )
                self.assertEqual(encrypted_files, [])
        finally:
            engine.dispose()
            storage_patch.stop()
            storage.cleanup()
            environment.stop()


if __name__ == "__main__":
    unittest.main()
