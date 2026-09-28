"""Protect case cleanup from racing upload-draft finalization."""

from __future__ import annotations

import asyncio
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastapi import UploadFile
from sqlalchemy import delete
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.models.auth import User
from backend.app.database.models.eeg import EEGSession
from backend.app.services.case_service import CaseReferenceError
from backend.app.services import session_service
from backend.app.services.session_service import create_upload_draft, finalize_upload_draft
from backend.app.services.storage_service import SessionStorage


class UploadDraftOwnerLockingTests(unittest.TestCase):
    def test_finalization_revalidates_after_last_case_deletion_wins_owner_lock(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        case_id = "CASE-ABCDEF12"

        with tempfile.TemporaryDirectory(prefix="upload-draft-case-race-") as directory:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            with Session(engine) as db:
                owner = User(
                    public_id="USR-upload-case-race-test",
                    email="upload-case-race-test@example.test",
                    password_hash="synthetic-only",
                )
                db.add(owner)
                db.commit()
                db.refresh(owner)
                assert owner.id is not None
                db.add(
                    EEGSession(
                        session_id="SES-CASE-RACE-BASELINE",
                        owner_user_id=owner.id,
                        case_id=case_id,
                    )
                )
                db.commit()
                draft = asyncio.run(
                    create_upload_draft(
                        db,
                        storage,
                        UploadFile(
                            filename="synthetic.zip",
                            file=io.BytesIO(b"PK\x03\x04synthetic"),
                        ),
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                        owner_user_id=owner.id,
                    )
                )
                draft_path = Path(draft.encrypted_path)

                original_lock = session_service.lock_owner_case_mutations
                original_validate = session_service.ensure_case_reference
                original_promote = storage.promote_draft
                events: list[str] = []
                promoted_paths: list[Path] = []

                def observe_validate(*args, **kwargs):
                    events.append("case-check")
                    return original_validate(*args, **kwargs)

                def observe_promote(draft_id: str, session_id: str) -> Path:
                    events.append("promote")
                    promoted_path = original_promote(draft_id, session_id)
                    promoted_paths.append(promoted_path)
                    return promoted_path

                def last_case_deletion_then_finalize_lock(
                    current_db: Session,
                    owner_user_id: int | None,
                ) -> None:
                    events.append("owner-lock")
                    pending_session = current_db.exec(
                        select(EEGSession).where(
                            EEGSession.upload_draft_id == draft.draft_id
                        )
                    ).first()
                    self.assertIsNone(
                        pending_session,
                        "finalization persisted a session before its owner lock",
                    )
                    original_lock(current_db, owner_user_id)
                    current_db.exec(
                        delete(EEGSession).where(
                            cast(Any, EEGSession.session_id) == "SES-CASE-RACE-BASELINE"
                        )
                    )
                    current_db.commit()
                    original_lock(current_db, owner_user_id)

                with (
                    patch.object(
                        session_service,
                        "ensure_case_reference",
                        side_effect=observe_validate,
                    ),
                    patch.object(
                        session_service,
                        "lock_owner_case_mutations",
                        side_effect=last_case_deletion_then_finalize_lock,
                    ),
                    patch.object(storage, "promote_draft", side_effect=observe_promote),
                    self.assertRaises(CaseReferenceError),
                ):
                    finalize_upload_draft(
                        db,
                        storage,
                        draft.draft_id,
                        owner_user_id=owner.id,
                        case_id=case_id,
                    )

                self.assertEqual(events, ["case-check", "promote", "owner-lock", "case-check"])
                self.assertEqual(len(promoted_paths), 1)
                self.assertFalse(promoted_paths[0].exists())
                self.assertTrue(draft_path.exists())
                self.assertIsNotNone(
                    session_service.get_upload_draft(db, draft.draft_id, owner.id)
                )
                self.assertIsNone(
                    db.exec(
                        select(EEGSession).where(
                            EEGSession.upload_draft_id == draft.draft_id
                        )
                    ).first()
                )


    def test_case_owner_lock_is_acquired_before_session_is_persisted(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        case_id = "CASE-ABCDEF12"

        with tempfile.TemporaryDirectory(prefix="upload-draft-owner-lock-") as directory:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            with Session(engine) as db:
                owner = User(
                    public_id="USR-upload-lock-test",
                    email="upload-lock-test@example.test",
                    password_hash="synthetic-only",
                )
                db.add(owner)
                db.commit()
                db.refresh(owner)
                assert owner.id is not None
                db.add(
                    EEGSession(
                        session_id="SES-CASE-BASELINE",
                        owner_user_id=owner.id,
                        case_id=case_id,
                    )
                )
                db.commit()
                draft = asyncio.run(
                    create_upload_draft(
                        db,
                        storage,
                        UploadFile(
                            filename="synthetic.zip",
                            file=io.BytesIO(b"PK\x03\x04synthetic"),
                        ),
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                        owner_user_id=owner.id,
                    )
                )

                acquire_owner_lock = session_service.lock_owner_case_mutations

                def assert_no_finalized_session_before_lock(
                    current_db: Session,
                    owner_user_id: int | None,
                ) -> None:
                    pending_session = current_db.exec(
                        select(EEGSession).where(
                            EEGSession.upload_draft_id == draft.draft_id
                        )
                    ).first()
                    self.assertIsNone(
                        pending_session,
                        "finalization inserted its session before acquiring the owner lock",
                    )
                    acquire_owner_lock(current_db, owner_user_id)

                with patch.object(
                    session_service,
                    "lock_owner_case_mutations",
                    side_effect=assert_no_finalized_session_before_lock,
                ):
                    result = finalize_upload_draft(
                        db,
                        storage,
                        draft.draft_id,
                        owner_user_id=owner.id,
                        case_id=case_id,
                    )

                self.assertTrue(result.created)
                self.assertEqual(result.session.case_id, case_id)
                self.assertEqual(
                    len(
                        db.exec(
                            select(EEGSession).where(
                                EEGSession.upload_draft_id == draft.draft_id
                            )
                        ).all()
                    ),
                    1,
                )
