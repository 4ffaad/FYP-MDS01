"""Serialize PDF replace/delete transitions on the case report row."""

from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from sqlalchemy import update
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.core import config
from backend.app.database.models.auth import User
from backend.app.database.models.case_source_report import CaseSourceReport
from backend.app.services import case_source_report_service as report_service

_SYNTHETIC_PDF = b"%PDF-1.4\nsynthetic row lock fixture\n%%EOF"


class CaseReportRowLockingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="case-report-lock-test-")
        key = base64.b64encode(b"x" * 32).decode("ascii")
        self.key_patch = patch.dict(os.environ, {config.STORAGE_KEY_ENV: key})
        self.key_patch.start()
        self.storage_patch = patch.object(
            config,
            "STORAGE_DIR",
            Path(self.temp.name) / "encrypted-storage",
        )
        self.storage_patch.start()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            owner = User(
                public_id="USR-report-lock-test",
                email="report-lock-test@example.test",
                password_hash="synthetic-only",
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)
            self.owner_id = owner.id
        assert self.owner_id is not None
        self.case_id = "CASE-REPORT-LOCK-TEST"

    def tearDown(self) -> None:
        self.engine.dispose()
        self.storage_patch.stop()
        self.key_patch.stop()
        self.temp.cleanup()

    def test_replace_and_delete_request_database_row_locks(self) -> None:
        owner_id = self.owner_id
        assert owner_id is not None
        with Session(self.engine) as db:
            report_service.save_case_source_report(
                db,
                case_id=self.case_id,
                owner_user_id=owner_id,
                pdf_bytes=_SYNTHETIC_PDF,
            )

        original_find = report_service._find_report
        with Session(self.engine) as db, patch.object(
            report_service,
            "_find_report",
            wraps=original_find,
        ) as find_report:
            report_service.save_case_source_report(
                db,
                case_id=self.case_id,
                owner_user_id=owner_id,
                pdf_bytes=_SYNTHETIC_PDF + b" replacement",
            )
            self.assertTrue(
                any(call.kwargs.get("for_update") is True for call in find_report.call_args_list)
            )

        with Session(self.engine) as db, patch.object(
            report_service,
            "_find_report",
            wraps=original_find,
        ) as find_report:
            self.assertTrue(
                report_service.delete_case_source_report(
                    db,
                    case_id=self.case_id,
                    owner_user_id=owner_id,
                )
            )
            self.assertTrue(
                any(call.kwargs.get("for_update") is True for call in find_report.call_args_list)
            )
            self.assertIsNone(
                db.exec(
                    select(CaseSourceReport).where(
                        CaseSourceReport.case_id == self.case_id,
                        CaseSourceReport.owner_user_id == owner_id,
                    )
                ).first()
            )

    def test_locked_tombstone_refreshes_a_preloaded_report_row(self) -> None:
        owner_id = self.owner_id
        assert owner_id is not None
        stale_cleanup_id = "a" * 32
        active_artifact_id = "b" * 32
        with Session(self.engine) as db:
            row = CaseSourceReport(
                case_id=self.case_id,
                owner_user_id=owner_id,
                artifact_id=None,
                cleanup_artifact_id=stale_cleanup_id,
                crypto_version=1,
            )
            db.add(row)
            db.commit()
            preloaded = report_service._find_report(
                db, case_id=self.case_id, owner_user_id=owner_id
            )
            assert preloaded is not None
            db.exec(
                update(CaseSourceReport)
                .where(cast(Any, CaseSourceReport.case_id) == self.case_id)
                .values(artifact_id=active_artifact_id, cleanup_artifact_id=None)
                .execution_options(synchronize_session=False)
            )
            with patch.object(report_service, "_remove_artifact") as remove:
                report_service._settle_cleanup_pointer(db, preloaded)
                remove.assert_not_called()
            self.assertEqual(preloaded.artifact_id, active_artifact_id)
            self.assertIsNone(preloaded.cleanup_artifact_id)
