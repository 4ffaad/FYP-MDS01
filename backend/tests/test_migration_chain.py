"""Exercise the restored Alembic chain against disposable SQLite databases."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG = REPOSITORY_ROOT / "backend" / "alembic.ini"
EXPECTED_HEAD = "035_video_until_deletion"


class MigrationChainTests(unittest.TestCase):
    def test_current_revision_id_fits_alembic_version_column(self) -> None:
        self.assertLessEqual(len(EXPECTED_HEAD), 32)

    def _run_alembic(self, database_url: str, *arguments: str) -> None:
        environment = os.environ.copy()
        environment["DATABASE_URL"] = database_url
        python_path = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(REPOSITORY_ROOT), python_path) if part
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(ALEMBIC_CONFIG),
                *arguments,
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            self.fail(
                f"Alembic {' '.join(arguments)} failed with {result.returncode}:\n"
                f"{result.stdout[-2000:]}\n{result.stderr[-4000:]}"
            )

    def _assert_owner_scoped_schema(self, database_path: Path) -> None:
        with sqlite3.connect(database_path) as connection:
            head = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            self.assertEqual((EXPECTED_HEAD,), head)

            report_columns = connection.execute(
                "PRAGMA table_info(case_source_reports)"
            ).fetchall()
            report_primary_key = [
                column[1]
                for column in sorted(report_columns, key=lambda column: column[5])
                if column[5]
            ]
            self.assertEqual(["owner_user_id", "case_id"], report_primary_key)

            privacy_columns = {
                column[1]
                for column in connection.execute(
                    "PRAGMA table_info(video_privacy_jobs)"
                )
            }
            self.assertIn("idempotency_key_hash", privacy_columns)
            self.assertIn("content_fingerprint", privacy_columns)

            detection_columns = {
                column[1]
                for column in connection.execute(
                    "PRAGMA table_info(video_detection_jobs)"
                )
            }
            self.assertIn("review_privacy_method", detection_columns)

            detection_columns = {
                column[1]: column
                for column in connection.execute(
                    "PRAGMA table_info(video_detection_jobs)"
                )
            }
            self.assertIn("blur_strength_percent", detection_columns)
            self.assertEqual(1, detection_columns["blur_strength_percent"][3])
            self.assertEqual("100", detection_columns["blur_strength_percent"][4])
            for name in (
                "source_name_token",
                "source_group_id",
                "sync_group_complete",
                "eeg_recording_db_id",
                "eeg_sync_status",
                "eeg_sync_nonce",
                "eeg_sync_ciphertext",
            ):
                self.assertIn(name, detection_columns)

            recording_columns = {
                column[1]
                for column in connection.execute("PRAGMA table_info(recordings)")
            }
            self.assertTrue(
                {"video_sync_status", "video_sync_nonce", "video_sync_ciphertext"}
                <= recording_columns
            )

            profile_columns = {
                column[1]: column for column in connection.execute(
                    "PRAGMA table_info(case_patient_profiles)"
                )
            }
            self.assertIn("verification_status", profile_columns)
            self.assertEqual(0, profile_columns["reviewed_by_user_id"][3])
            self.assertEqual(0, profile_columns["reviewed_at"][3])

            annotation_columns = {
                column[1]
                for column in connection.execute(
                    "PRAGMA table_info(clinical_annotations)"
                )
            }
            self.assertTrue(
                {
                    "annotation_id",
                    "recording_db_id",
                    "owner_user_id",
                    "created_by_user_id",
                    "payload_nonce",
                    "payload_ciphertext",
                    "crypto_version",
                }
                <= annotation_columns
            )

            access_columns = {
                column[1]
                for column in connection.execute(
                    "PRAGMA table_info(clinical_access_events)"
                )
            }
            self.assertTrue(
                {
                    "actor_user_id",
                    "recording_db_id",
                    "session_db_id",
                    "video_job_db_id",
                    "action",
                    "created_at",
                }
                <= access_columns
            )

    def test_upgrade_from_021_reaches_current_owner_scoped_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mds01-alembic-021-") as directory:
            database_path = Path(directory) / "migration.sqlite3"
            database_url = f"sqlite:///{database_path}"
            self._run_alembic(database_url, "upgrade", "021_recording_provenance")
            self._run_alembic(database_url, "upgrade", "head")
            self._assert_owner_scoped_schema(database_path)

    def test_upgrade_and_downgrade_from_025_handles_unnamed_primary_key(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mds01-alembic-025-") as directory:
            database_path = Path(directory) / "migration.sqlite3"
            database_url = f"sqlite:///{database_path}"
            self._run_alembic(database_url, "upgrade", "025_case_source_report")
            self._run_alembic(database_url, "upgrade", "head")
            self._assert_owner_scoped_schema(database_path)
            self._run_alembic(database_url, "downgrade", "025_case_source_report")
            self._run_alembic(database_url, "upgrade", "head")
            self._assert_owner_scoped_schema(database_path)

    def test_upgrade_retains_non_expired_video_jobs_without_deadlines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mds01-video-retention-") as directory:
            database_path = Path(directory) / "migration.sqlite3"
            database_url = f"sqlite:///{database_path}"
            self._run_alembic(database_url, "upgrade", "034_clinical_annotations")
            with sqlite3.connect(database_path) as connection:
                for job_id, status, expires_at in (
                    ("VID-READY", "ready", "2030-01-01 00:00:00"),
                    ("VID-FAILED", "failed", "2030-01-01 00:00:00"),
                    ("VID-EXPIRED", "expired", "2020-01-01 00:00:00"),
                ):
                    connection.execute(
                        """INSERT INTO video_detection_jobs
                        (owner_user_id, job_id, status, current_stage,
                         duration_seconds, fps, created_at, retention_expires_at)
                        VALUES (?, ?, ?, 'complete', 10, 30,
                                '2026-01-01 00:00:00', ?)""",
                        (1, job_id, status, expires_at),
                    )
                connection.commit()

            self._run_alembic(database_url, "upgrade", "head")
            with sqlite3.connect(database_path) as connection:
                retention = dict(
                    connection.execute(
                        "SELECT job_id, retention_expires_at FROM video_detection_jobs"
                    ).fetchall()
                )
            self.assertIsNone(retention["VID-READY"])
            self.assertIsNone(retention["VID-FAILED"])
            self.assertIsNotNone(retention["VID-EXPIRED"])


if __name__ == "__main__":
    unittest.main()
