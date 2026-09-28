"""Strict native-resolution admission tests without real patient video."""

from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import UploadFile
from starlette.datastructures import Headers

from backend.app.services import video_detection_service as service
from backend.app.services.storage_service import StorageError
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_detection.contract import DetectionError
from backend.app.video_privacy import processor as privacy_processor
from backend.app.video_privacy.processor import VideoProcessorError


class VideoPreflightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.storage = MagicMock()
        self.storage.save_upload = AsyncMock(return_value=Path("/private/encrypted-video"))
        self.upload = UploadFile(
            filename="clip.avi",
            file=io.BytesIO(b"synthetic video bytes"),
            headers=Headers({"content-type": "video/x-msvideo"}),
        )

    async def test_preflight_decoder_timeout_uses_killable_secret_free_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "synthetic.input"
            source.write_bytes(b"synthetic encrypted-test fixture")
            timeout = 0.125
            runner = getattr(privacy_processor, "preflight_video_subprocess", None)
            if not callable(runner):
                self.fail("preflight must run in a killable worker process")
            with patch.dict(
                os.environ,
                {
                    "MDS01_STORAGE_KEY": "synthetic-storage-secret",
                    "DATABASE_URL": "postgresql://synthetic-private-db",
                    "VSVIG_ASSET_DIR": "/opt/synthetic-assets",
                    "VSVIG_CONTRACT_SHA256": "b" * 64,
                },
                clear=True,
            ), patch(
                "backend.app.video_privacy.processor.subprocess.run",
                side_effect=subprocess.TimeoutExpired("synthetic-worker", timeout),
            ) as run:
                with self.assertRaisesRegex(VideoProcessorError, "preflight timed out"):
                    runner(
                        source,
                        timeout_seconds=timeout,
                    )

            command = run.call_args.args[0]
            options = run.call_args.kwargs
            self.assertIn("--preflight-worker", command)
            self.assertEqual(options["timeout"], timeout)
            self.assertTrue(options["check"])
            environment = options["env"]
            self.assertNotIn("MDS01_STORAGE_KEY", environment)
            self.assertNotIn("DATABASE_URL", environment)
            self.assertEqual(environment["VSVIG_ASSET_DIR"], "/opt/synthetic-assets")
            self.assertEqual(environment["VSVIG_CONTRACT_SHA256"], "b" * 64)
            self.assertEqual(list(Path(directory).glob(".video-preflight-*.json")), [])

    async def test_synthetic_invalid_clip_uses_the_isolated_worker_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "not-video.mp4"
            source.write_bytes(b"synthetic invalid video data")
            runner = getattr(privacy_processor, "preflight_video_subprocess", None)
            if not callable(runner):
                self.fail("preflight must run in an isolated process")
            with self.assertRaisesRegex(VideoProcessorError, "could not be validated safely"):
                runner(source, timeout_seconds=5)

    async def test_standalone_preflight_orphan_is_recovered_by_age_bounded_sweep(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(Path(directory) / "sessions", storage_key=b"u" * 32)
            upload = UploadFile(
                filename="synthetic.avi",
                file=io.BytesIO(b"synthetic encrypted payload"),
                headers=Headers({"content-type": "video/x-msvideo"}),
            )
            with patch.object(
                service,
                "_preflight_uploaded_video",
                return_value={"fps": 24.0, "width": 1920, "height": 1080, "frame_count": 48},
            ), patch.object(storage, "delete_job", side_effect=OSError("synthetic cleanup failure")):
                with self.assertRaises(StorageError):
                    await service.preflight_video_upload(storage, upload)

            orphans = list(storage.root.glob("VID-PREFLIGHT-*"))
            self.assertEqual(len(orphans), 1)
            orphan = orphans[0]
            old_time = time.time() - 3600
            for path in [*orphan.rglob("*"), orphan]:
                os.utime(path, (old_time, old_time), follow_symlinks=False)

            fresh = storage.root / ("VID-PREFLIGHT-" + "F" * 24)
            (fresh / "original").mkdir(parents=True)
            (fresh / "original" / "video.input.enc").write_bytes(b"synthetic-current")
            unrelated = storage.root / ("VID-" + "A" * 32)
            unrelated.mkdir()

            removed = storage.cleanup_stale_preflight_uploads(
                max_age_seconds=60,
                now=time.time(),
            )
            self.assertEqual(removed, 1)
            self.assertFalse(orphan.exists())
            self.assertTrue(fresh.exists())
            self.assertTrue(unrelated.exists())

    def test_preflight_orphan_sweep_skips_active_upload_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(Path(directory) / "sessions", storage_key=b"w" * 32)
            job_id = "VID-PREFLIGHT-" + "A" * 24
            with storage.preflight_upload_lease(job_id):
                job_root = storage.root / job_id
                original = job_root / "original"
                original.mkdir(parents=True)
                (original / "video.input.enc").write_bytes(b"synthetic-current")
                old_time = time.time() - 3600
                for path in [*job_root.rglob("*"), job_root]:
                    os.utime(path, (old_time, old_time), follow_symlinks=False)

                removed_while_active = storage.cleanup_stale_preflight_uploads(
                    max_age_seconds=60,
                    now=time.time(),
                )
                self.assertEqual(removed_while_active, 0)
                self.assertTrue(job_root.exists())

            removed_after_release = storage.cleanup_stale_preflight_uploads(
                max_age_seconds=60,
                now=time.time(),
            )
            self.assertEqual(removed_after_release, 1)
            self.assertFalse(job_root.exists())

    async def test_native_resolution_preflight_reports_640_by_480_and_deletes_temporary_media(self) -> None:
        with patch.object(
            service,
            "_preflight_uploaded_video",
            return_value={"width": 640, "height": 480, "fps": 25.0, "frame_count": 250},
        ):
            result = await service.preflight_video_upload(self.storage, self.upload)

        self.assertFalse(result["accepted"])
        self.assertEqual((result["width"], result["height"]), (640, 480))
        self.assertEqual((result["required_width"], result["required_height"]), (1920, 1080))
        self.assertIn("operator to enable experimental letterboxing", result["message"])
        self.storage.delete_job.assert_called_once()
        self.assertTrue(self.upload.file.closed)

    async def test_native_resolution_preflight_accepts_only_exact_contract_geometry(self) -> None:
        with patch.object(
            service,
            "_preflight_uploaded_video",
            return_value={"width": 1920, "height": 1080, "fps": 25.0, "frame_count": 250},
        ):
            result = await service.preflight_video_upload(self.storage, self.upload)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["duration_seconds"], 10.0)
        self.assertIn("synchronization is not established", result["message"])

    async def test_letterbox_preflight_is_marked_experimental_when_enabled(self) -> None:
        with patch.object(service, "VSVIG_ALLOW_LETTERBOX_ADAPTATION", True, create=True), patch.object(
            service,
            "_preflight_uploaded_video",
            return_value={"width": 640, "height": 480, "fps": 25.0, "frame_count": 250},
        ):
            result = await service.preflight_video_upload(self.storage, self.upload)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["adaptation"], "letterbox")
        self.assertTrue(result["experimental"])
        self.assertIn("not been validated as equivalent", result["message"])

    async def test_job_admission_rejects_lower_resolution_even_if_preflight_is_bypassed(self) -> None:
        database = MagicMock()
        storage = MagicMock()
        storage.save_upload = AsyncMock(return_value=Path("/private/encrypted-video"))
        upload = UploadFile(
            filename="clip.avi",
            file=io.BytesIO(b"synthetic video bytes"),
            headers=Headers({"content-type": "video/x-msvideo"}),
        )
        with (
            patch.object(service, "load_contract"),
            patch.object(
                service,
                "_preflight_uploaded_video",
                return_value={"width": 640, "height": 480, "fps": 25.0, "frame_count": 250},
            ),
            patch.object(service, "cleanup_case_profile_if_empty"),
            self.assertRaises(DetectionError) as raised,
        ):
            await service.create_job(database, storage, upload, owner=7)

        self.assertEqual(str(raised.exception), "video_resolution_mismatch")
        storage.delete_job.assert_called_once()
        database.delete.assert_called_once()

    async def test_job_admission_accepts_lower_resolution_only_when_letterbox_is_enabled(self) -> None:
        database = MagicMock()
        storage = MagicMock()
        storage.save_upload = AsyncMock(return_value=Path("/private/encrypted-video"))
        upload = UploadFile(
            filename="clip.avi",
            file=io.BytesIO(b"synthetic video bytes"),
            headers=Headers({"content-type": "video/x-msvideo"}),
        )
        with patch.object(service, "VSVIG_ALLOW_LETTERBOX_ADAPTATION", True, create=True), patch.object(
            service, "load_contract"
        ), patch.object(
            service,
            "_preflight_uploaded_video",
            return_value={"width": 640, "height": 480, "fps": 25.0, "frame_count": 250},
        ):
            job = await service.create_job(database, storage, upload, owner=7)

        self.assertEqual(job.duration_seconds, 10.0)
        storage.delete_job.assert_not_called()


if __name__ == "__main__":
    unittest.main()
