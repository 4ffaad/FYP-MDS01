"""Regression tests for defects found during the FYP verification review."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import main as main_module
from backend.app.services.processing_service import _sha256_file


class ReviewRegressionTests(unittest.TestCase):
    def test_invalid_model_runtime_aborts_before_startup_side_effects(self) -> None:
        async def start_application() -> None:
            async with main_module.lifespan(main_module.app):
                self.fail("lifespan must reject an unsupported model runtime")

        with (
            patch.object(main_module, "MODEL_RUNTIME", "typo-runtime"),
            patch.object(
                main_module, "auth_configuration", return_value=("local", "", "")
            ) as auth_configuration,
            patch.object(main_module, "_purge_auth_sessions"),
            patch.object(main_module, "sweep_interrupted_sessions"),
            patch.object(main_module, "sweep_expired_upload_drafts"),
            patch("backend.app.services.video_detection_service.sweep"),
            patch("backend.app.services.video_privacy_service.sweep_video_privacy_jobs"),
        ):
            with self.assertRaisesRegex(RuntimeError, "MODEL_RUNTIME"):
                asyncio.run(start_application())

        auth_configuration.assert_not_called()

    def test_nicolet_data_provenance_checksum_includes_head_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "recording.data"
            head_path = data_path.with_suffix(".head")
            data_path.write_bytes(b"same signal bytes")
            head_path.write_bytes(b"first interpretation header")

            first_checksum = _sha256_file(data_path)
            self.assertEqual(_sha256_file(data_path), first_checksum)

            head_path.write_bytes(b"different interpretation header")
            second_checksum = _sha256_file(data_path)

        self.assertNotEqual(first_checksum, second_checksum)


if __name__ == "__main__":
    unittest.main()
