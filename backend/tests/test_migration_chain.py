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
EXPECTED_HEAD = "029_profile_verification_status"


class MigrationChainTests(unittest.TestCase):
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

            profile_columns = {
                column[1]: column for column in connection.execute(
                    "PRAGMA table_info(case_patient_profiles)"
                )
            }
            self.assertIn("verification_status", profile_columns)
            self.assertEqual(0, profile_columns["reviewed_by_user_id"][3])
            self.assertEqual(0, profile_columns["reviewed_at"][3])

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


if __name__ == "__main__":
    unittest.main()
