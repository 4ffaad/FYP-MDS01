"""Configuration safety regressions."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from unittest.mock import MagicMock

from backend.app.core.config import configured_cors_origins, ensure_runtime_directories


class ConfigurationTests(unittest.TestCase):
    def test_production_cors_requires_exact_https_non_local_origins(self) -> None:
        for value in ("", "http://app.example.test", "https://localhost:3000"):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"APP_ENV": "production", "CORS_ORIGINS": value},
                clear=False,
            ):
                with self.assertRaises(RuntimeError):
                    configured_cors_origins()

    def test_postgres_runtime_does_not_touch_sqlite_directory(self) -> None:
        with self.subTest("postgres"), patch(
            "backend.app.core.config.DATABASE_URL", "postgresql+psycopg://db/analysis"
        ), patch("backend.app.core.config.DATABASE_DIR", MagicMock()) as database_dir:
            with patch("backend.app.core.config.SESSION_STORAGE_DIR") as storage_root:
                storage_root.mkdir.return_value = None
                storage_root.chmod.return_value = None
                ensure_runtime_directories()
        database_dir.mkdir.assert_not_called()

    def test_production_cors_accepts_explicit_https_origins(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "CORS_ORIGINS": "https://review.example.test"},
            clear=False,
        ):
            self.assertEqual(configured_cors_origins(), ("https://review.example.test",))


if __name__ == "__main__":
    unittest.main()
