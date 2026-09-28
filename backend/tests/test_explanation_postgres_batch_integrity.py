"""Opt-in disposable-PostgreSQL regression for batched EEG explanations."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import time
import unittest
from urllib.parse import quote_plus

from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.models.eeg import EEGRecording, EEGSession, Explanation, Prediction
from backend.app.database.repository import list_predictions_for_processing


@unittest.skipUnless(
    os.environ.get("MDS01_RUN_DISPOSABLE_POSTGRES_TESTS") == "1",
    "set MDS01_RUN_DISPOSABLE_POSTGRES_TESTS=1 to run disposable PostgreSQL tests",
)
class ExplanationPostgresBatchIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("docker") is None:
            raise unittest.SkipTest("Docker CLI is unavailable")
        cls.container_name = f"mds01-explanation-batch-{secrets.token_hex(6)}"
        cls.password = secrets.token_hex(24)
        started = subprocess.run(
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
                "POSTGRES_DB=mds01_explanation_test",
                "--publish",
                "127.0.0.1::5432",
                "postgres:16-alpine",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise RuntimeError("Could not start disposable PostgreSQL for the regression test")
        try:
            port_result = subprocess.run(
                ["docker", "port", cls.container_name, "5432/tcp"],
                check=False,
                capture_output=True,
                text=True,
            )
            if port_result.returncode != 0 or not port_result.stdout.strip():
                raise RuntimeError("Could not resolve disposable PostgreSQL port")
            port = int(port_result.stdout.strip().splitlines()[0].rsplit(":", 1)[1])
            cls.database_url = (
                f"postgresql+psycopg://postgres:{quote_plus(cls.password)}"
                f"@127.0.0.1:{port}/mds01_explanation_test"
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
                        "mds01_explanation_test",
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
                raise RuntimeError("Disposable PostgreSQL did not become ready")
            cls.engine = create_engine(cls.database_url, pool_pre_ping=True)
            SQLModel.metadata.create_all(cls.engine)
        except Exception:
            subprocess.run(
                ["docker", "rm", "--force", cls.container_name],
                check=False,
                capture_output=True,
            )
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

    def test_thousand_explanations_reference_committed_prediction_rows(self) -> None:
        with Session(self.engine) as db:
            session = EEGSession(session_id="SES-PG-EXPLANATION-BATCH")
            db.add(session)
            db.commit()
            db.refresh(session)

            record = EEGRecording(
                record_id="REC-PG-EXPLANATION-BATCH",
                session_db_id=session.id or 0,
                sequence_index=1,
                original_filename="synthetic.e",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            record_db_id = record.id or 0

            predictions = [
                Prediction(
                    recording_db_id=record.id or 0,
                    window_index=index,
                    model_name="development-stub",
                    model_version="stub-0.1.0",
                    threshold=0.5,
                    probability=0.9,
                    raw_score=0.9,
                    score_type="development_score",
                    seizure_detected=True,
                    start_seconds=float(index * 2),
                    end_seconds=float(index * 2 + 4),
                )
                for index in range(1000)
            ]
            db.add_all(predictions)
            db.commit()

            stored_predictions = list_predictions_for_processing(db, record_db_id)
            self.assertEqual(len(stored_predictions), 1000)
            db.add_all(
                Explanation(
                    prediction_db_id=prediction.id or 0,
                    method="synthetic-stub",
                    explanation_path="",
                    explanation_data="{}",
                    is_clinical=False,
                )
                for prediction in stored_predictions
            )
            db.commit()

        with Session(self.engine) as db:
            prediction_ids = db.exec(
                select(Prediction.id).where(
                    Prediction.recording_db_id == record_db_id
                )
            ).all()
            explanation_prediction_ids = db.exec(
                select(Explanation.prediction_db_id).order_by(Explanation.id)
            ).all()
            explanation_count = db.exec(select(func.count()).select_from(Explanation)).one()
            orphan_count = db.exec(
                select(func.count())
                .select_from(Explanation)
                .outerjoin(Prediction, Explanation.prediction_db_id == Prediction.id)
                .where(Prediction.id.is_(None))
            ).one()

        self.assertEqual(len(prediction_ids), 1000)
        self.assertEqual(explanation_count, 1000)
        self.assertEqual(orphan_count, 0)
        self.assertEqual(set(explanation_prediction_ids), set(prediction_ids))


if __name__ == "__main__":
    unittest.main()
