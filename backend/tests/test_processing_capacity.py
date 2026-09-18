"""Security checks for bounded in-process EEG processing."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks, HTTPException

from backend.app.services.processing_capacity import ProcessingCapacity


class ProcessingCapacityTests(unittest.TestCase):
    def test_capacity_rejects_parallel_work_and_recovers_after_completion(self) -> None:
        processed: list[str] = []
        capacity = ProcessingCapacity(limit=1, processor=processed.append)

        self.assertTrue(capacity.reserve())
        self.assertFalse(capacity.reserve())
        capacity.run_reserved("SES-ONE")
        self.assertEqual(processed, ["SES-ONE"])
        self.assertTrue(capacity.reserve())

    def test_capacity_is_released_when_processing_fails(self) -> None:
        def fail(_session_id: str) -> None:
            raise RuntimeError("failed")

        capacity = ProcessingCapacity(limit=1, processor=fail)
        self.assertTrue(capacity.reserve())
        with self.assertRaises(RuntimeError):
            capacity.run_reserved("SES-FAIL")
        self.assertTrue(capacity.reserve())

    def test_upload_is_rejected_before_session_creation_when_capacity_is_full(self) -> None:
        from backend.app.api.sessions import upload_session

        with (
            patch("backend.app.api.sessions.processing_capacity.reserve", return_value=False),
            patch("backend.app.api.sessions.create_session") as create_session,
        ):
            with self.assertRaises(HTTPException) as raised:
                import asyncio
                import io
                from fastapi import UploadFile

                asyncio.run(
                    upload_session(
                        BackgroundTasks(),
                        UploadFile(filename="session.zip", file=io.BytesIO(b"zip")),
                        "metadata-scrub",
                    )
                )

        self.assertEqual(raised.exception.status_code, 503)
        create_session.assert_not_called()

    def test_draft_finalize_releases_capacity_if_cleanup_fails_before_promotion(self) -> None:
        from backend.app.api.uploads import finalize_staged_upload
        from backend.app.services.storage_service import StorageError

        with (
            patch("backend.app.api.uploads.processing_capacity.reserve", return_value=True),
            patch("backend.app.api.uploads.processing_capacity.release") as release,
            patch("backend.app.api.uploads.SessionStorage"),
            patch(
                "backend.app.api.uploads.cleanup_expired_drafts",
                side_effect=StorageError("cleanup failed at /private/sessions/SES-1"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                finalize_staged_upload(
                    "DRAFT-ONE", BackgroundTasks(), None, db=MagicMock(), current_user=None
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("/private/sessions", str(raised.exception.detail))
        release.assert_called_once_with()

    def test_draft_finalize_maps_storage_failure_to_503(self) -> None:
        from backend.app.api.uploads import finalize_staged_upload
        from backend.app.services.storage_service import StorageError

        with (
            patch("backend.app.api.uploads.processing_capacity.reserve", return_value=True),
            patch("backend.app.api.uploads.processing_capacity.release") as release,
            patch("backend.app.api.uploads.SessionStorage"),
            patch("backend.app.api.uploads.cleanup_expired_drafts"),
            patch(
                "backend.app.api.uploads.finalize_upload_draft",
                side_effect=StorageError("storage unavailable"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                finalize_staged_upload(
                    "DRAFT-ONE", BackgroundTasks(), None, db=MagicMock(), current_user=None
                )

        self.assertEqual(raised.exception.status_code, 503)
        release.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
