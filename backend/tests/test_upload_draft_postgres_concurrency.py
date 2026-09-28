"""Opt-in PostgreSQL race regression using a disposable local container."""

from __future__ import annotations

import asyncio
import io
import multiprocessing
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from urllib.parse import quote_plus

from fastapi import UploadFile
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database import models as _registered_models  # noqa: F401
from backend.app.database.models.auth import User
from backend.app.database.models.eeg import AnalysisStatus, EEGSession, UploadDraft
from backend.app.services.case_service import CaseReferenceError
from backend.app.services.session_service import create_upload_draft
from backend.app.services.storage_service import SessionStorage


def _finalize_worker(
    database_url: str,
    storage_root: str,
    storage_key_hex: str,
    draft_id: str,
    owner_user_id: int,
    case_id: str,
    promoted,
    continue_finalization,
    result_queue,
) -> None:
    from backend.app.services.session_service import finalize_upload_draft

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            storage = SessionStorage(Path(storage_root), bytes.fromhex(storage_key_hex))
            promote = storage.promote_draft

            def pause_after_promotion(draft_id: str, session_id: str) -> Path:
                path = promote(draft_id, session_id)
                promoted.set()
                if not continue_finalization.wait(30):
                    raise TimeoutError("test coordinator did not resume finalization")
                return path

            with patch.object(storage, "promote_draft", side_effect=pause_after_promotion):
                try:
                    result = finalize_upload_draft(
                        db,
                        storage,
                        draft_id,
                        owner_user_id=owner_user_id,
                        case_id=case_id,
                    )
                    result_queue.put(("finalized", result.session.session_id))
                except CaseReferenceError:
                    result_queue.put(("case-missing",))
                except BaseException as exc:
                    result_queue.put(("error", type(exc).__name__, str(exc)))
    finally:
        engine.dispose()


def _delete_last_case_worker(
    database_url: str,
    storage_root: str,
    storage_key_hex: str,
    session_id: str,
    owner_user_id: int,
    result_queue,
) -> None:
    from backend.app.services.session_service import delete_session

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            session = db.exec(
                select(EEGSession).where(
                    EEGSession.session_id == session_id,
                    EEGSession.owner_user_id == owner_user_id,
                )
            ).one()
            storage = SessionStorage(Path(storage_root), bytes.fromhex(storage_key_hex))
            delete_session(db, storage, session)
            result_queue.put(("deleted-last-case",))
    except BaseException as exc:
        result_queue.put(("error", type(exc).__name__, str(exc)))
    finally:
        engine.dispose()


def _concurrent_finalize_worker(
    database_url: str,
    storage_root: str,
    storage_key_hex: str,
    draft_id: str,
    owner_user_id: int,
    case_id: str,
    owner_lock_barrier,
    result_queue,
) -> None:
    from backend.app.services import session_service
    from backend.app.services.session_service import finalize_upload_draft

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            storage = SessionStorage(Path(storage_root), bytes.fromhex(storage_key_hex))
            acquire_owner_lock = session_service.lock_owner_case_mutations

            def synchronize_owner_lock(current_db: Session, current_owner_id: int | None) -> None:
                owner_lock_barrier.wait(timeout=30)
                acquire_owner_lock(current_db, current_owner_id)

            with patch.object(
                session_service,
                "lock_owner_case_mutations",
                side_effect=synchronize_owner_lock,
            ):
                try:
                    result = finalize_upload_draft(
                        db,
                        storage,
                        draft_id,
                        owner_user_id=owner_user_id,
                        case_id=case_id,
                    )
                    result_queue.put(("finalized", result.session.session_id))
                except BaseException as exc:
                    original = getattr(exc, "orig", None)
                    sqlstate = getattr(original, "sqlstate", None) or getattr(
                        original, "pgcode", None
                    )
                    result_queue.put(("error", type(exc).__name__, sqlstate))
    finally:
        engine.dispose()


@unittest.skipUnless(
    os.environ.get("MDS01_RUN_DISPOSABLE_POSTGRES_TESTS") == "1",
    "set MDS01_RUN_DISPOSABLE_POSTGRES_TESTS=1 to run disposable PostgreSQL races",
)
class UploadDraftPostgresConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("docker") is None:
            raise unittest.SkipTest("Docker CLI is unavailable")
        cls.container_name = f"mds01-draft-race-{secrets.token_hex(6)}"
        cls.password = secrets.token_hex(24)
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="mds01-draft-race-",
            dir=os.environ.get("TMPDIR"),
        )
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--rm",
                    "--name",
                    cls.container_name,
                    "--env",
                    f"POSTGRES_PASSWORD={cls.password}",
                    "--env",
                    "POSTGRES_DB=mds01_disposable_test",
                    "--publish",
                    "127.0.0.1::5432",
                    "postgres:16-alpine",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            port_output = subprocess.run(
                ["docker", "port", cls.container_name, "5432/tcp"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip().splitlines()[0]
            port = int(port_output.rsplit(":", 1)[1])
            cls.database_url = (
                f"postgresql+psycopg://postgres:{quote_plus(cls.password)}"
                f"@127.0.0.1:{port}/mds01_disposable_test"
            )
            ready = False
            for _attempt in range(80):
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        cls.container_name,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-p",
                        "5432",
                        "-U",
                        "postgres",
                        "-d",
                        "mds01_disposable_test",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    ready = True
                    break
                time.sleep(0.25)
            if not ready:
                raise RuntimeError("disposable PostgreSQL container did not become ready")
            cls.engine = create_engine(cls.database_url, pool_pre_ping=True)
            SQLModel.metadata.create_all(cls.engine)
        except Exception:
            subprocess.run(
                ["docker", "rm", "--force", cls.container_name],
                check=False,
                capture_output=True,
            )
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "engine"):
            cls.engine.dispose()
        if hasattr(cls, "container_name"):
            subprocess.run(
                ["docker", "rm", "--force", cls.container_name],
                check=False,
                capture_output=True,
            )
        if hasattr(cls, "temporary"):
            cls.temporary.cleanup()

    def test_last_case_delete_wins_before_finalize(self) -> None:
        context = multiprocessing.get_context("spawn")
        storage_root = Path(self.temporary.name) / "private-sessions"
        storage_key = b"p" * 32
        case_id = "CASE-ABCDE123"
        baseline_session_id = "SES-PG-BASELINE"
        with Session(self.engine) as db:
            owner = User(
                public_id=f"USR-{secrets.token_hex(8)}",
                email=f"{secrets.token_hex(8)}@example.test",
                password_hash="synthetic-only",
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)
            assert owner.id is not None
            owner_user_id = owner.id
            db.add(
                EEGSession(
                    session_id=baseline_session_id,
                    owner_user_id=owner_user_id,
                    case_id=case_id,
                    status=AnalysisStatus.COMPLETED,
                )
            )
            db.commit()
            storage = SessionStorage(storage_root, storage_key)
            draft = asyncio.run(
                create_upload_draft(
                    db,
                    storage,
                    UploadFile(
                        filename="synthetic.zip",
                        file=io.BytesIO(b"PK\x03\x04synthetic"),
                    ),
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    owner_user_id=owner_user_id,
                )
            )
        draft_id = draft.draft_id
        draft_path = Path(draft.encrypted_path)
        storage_key_hex = storage_key.hex()
        promoted = context.Event()
        continue_finalization = context.Event()
        finalize_results = context.Queue()
        finalizer = context.Process(
            target=_finalize_worker,
            args=(
                self.database_url,
                str(storage_root),
                storage_key_hex,
                draft_id,
                owner_user_id,
                case_id,
                promoted,
                continue_finalization,
                finalize_results,
            ),
        )
        last_case_results = context.Queue()
        last_case_deleter = context.Process(
            target=_delete_last_case_worker,
            args=(
                self.database_url,
                str(storage_root),
                storage_key_hex,
                baseline_session_id,
                owner_user_id,
                last_case_results,
            ),
        )

        finalizer.start()
        try:
            self.assertTrue(promoted.wait(30), "finalizer did not pause after promotion")
            last_case_deleter.start()
            last_case_deleter.join(30)
            self.assertFalse(last_case_deleter.is_alive(), "last-case deletion did not finish")
            self.assertEqual(last_case_results.get(timeout=2), ("deleted-last-case",))
        finally:
            continue_finalization.set()
            finalizer.join(30)

        self.assertFalse(finalizer.is_alive(), "finalizer did not exit")
        self.assertEqual(finalize_results.get(timeout=2), ("case-missing",))
        self.assertTrue(draft_path.exists())
        with Session(self.engine) as db:
            self.assertIsNone(
                db.exec(
                    select(EEGSession).where(
                        EEGSession.upload_draft_id == draft_id,
                    )
                ).first()
            )
            self.assertIsNotNone(
                db.exec(select(UploadDraft).where(UploadDraft.draft_id == draft_id)).first()
            )
        self.assertEqual(list(storage_root.glob("SES-*")), [])

    def test_concurrent_finalizations_lock_owner_before_session_foreign_key_check(self) -> None:
        context = multiprocessing.get_context("spawn")
        storage_root = Path(self.temporary.name) / "parallel-private-sessions"
        storage_key = b"q" * 32
        case_id = "CASE-ABCDEF56"
        with Session(self.engine) as db:
            owner = User(
                public_id=f"USR-{secrets.token_hex(8)}",
                email=f"{secrets.token_hex(8)}@example.test",
                password_hash="synthetic-only",
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)
            assert owner.id is not None
            owner_user_id = owner.id
            db.add(
                EEGSession(
                    session_id=f"SES-BASE-{secrets.token_hex(6)}",
                    owner_user_id=owner_user_id,
                    case_id=case_id,
                    status=AnalysisStatus.COMPLETED,
                )
            )
            db.commit()
            storage = SessionStorage(storage_root, storage_key)
            drafts = [
                asyncio.run(
                    create_upload_draft(
                        db,
                        storage,
                        UploadFile(
                            filename="synthetic.zip",
                            file=io.BytesIO(b"PK\x03\x04synthetic"),
                        ),
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                        owner_user_id=owner_user_id,
                    )
                )
                for _ in range(2)
            ]
            draft_ids = [draft.draft_id for draft in drafts]

        owner_lock_barrier = context.Barrier(2)
        result_queue = context.Queue()
        workers = [
            context.Process(
                target=_concurrent_finalize_worker,
                args=(
                    self.database_url,
                    str(storage_root),
                    storage_key.hex(),
                    draft_id,
                    owner_user_id,
                    case_id,
                    owner_lock_barrier,
                    result_queue,
                ),
            )
            for draft_id in draft_ids
        ]
        for worker in workers:
            worker.start()
        try:
            for worker in workers:
                worker.join(45)
            for worker in workers:
                self.assertFalse(worker.is_alive(), "concurrent finalization did not exit")
                self.assertEqual(worker.exitcode, 0)

            results = [result_queue.get(timeout=3) for _worker in workers]
            self.assertEqual(
                [result[0] for result in results],
                ["finalized", "finalized"],
                results,
            )
            finalized_draft_ids = set(draft_ids)
            with Session(self.engine) as db:
                sessions = list(
                    db.exec(
                        select(EEGSession).where(
                            cast(Any, EEGSession.upload_draft_id).in_(finalized_draft_ids)
                        )
                    ).all()
                )
                remaining_drafts = list(
                    db.exec(
                        select(UploadDraft).where(
                            cast(Any, UploadDraft.draft_id).in_(finalized_draft_ids)
                        )
                    ).all()
                )
            self.assertEqual(len(sessions), 2)
            self.assertEqual(remaining_drafts, [])
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                worker.join(5)

