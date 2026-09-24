"""Lifecycle regressions for standalone privacy jobs."""

import asyncio
from datetime import timedelta
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import subprocess

from fastapi import UploadFile
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
    utc_now,
)
from backend.app.services import video_privacy_service as service
from backend.app.services.video_storage_service import VideoStorage
from backend.app.video_privacy.processor import VideoProcessorError


class VideoPrivacyLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.database)

    def test_cancelled_upload_removes_queued_job(self) -> None:
        upload = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"))
        storage = VideoStorage()
        with patch.object(service, "engine", self.database), patch.object(
            storage, "save_upload", new=AsyncMock(side_effect=asyncio.CancelledError())
        ), patch.object(service, "new_video_job_id", return_value="VID-CANCELLED"):
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(
                    service.create_video_job(
                        Session(self.database),
                        storage,
                        upload,
                        VideoPrivacyProfile.FACE_REDACTED,
                        owner_user_id=1,
                    )
                )
        with Session(self.database) as db:
            self.assertIsNone(db.exec(select(VideoPrivacyJob)).first())

    def test_admission_cleanup_failure_persists_terminal_retry_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(root=Path(directory))
            encrypted = Path(directory) / "VID-CLEANUP" / "original" / "video.input.enc"
            encrypted.parent.mkdir(parents=True)
            encrypted.write_bytes(b"ciphertext")
            upload = UploadFile(filename="patient.mp4", file=io.BytesIO(b"private-source"))
            with patch.object(service, "new_video_job_id", return_value="VID-CLEANUP"), patch.object(
                storage, "save_upload", new=AsyncMock(return_value=encrypted)
            ), patch.object(service, "_preflight_uploaded_video", side_effect=ValueError("bad video")), patch.object(
                storage, "delete_job", side_effect=OSError("cleanup unavailable")
            ):
                with self.assertRaises(ValueError):
                    asyncio.run(
                        service.create_video_job(
                            Session(self.database),
                            storage,
                            upload,
                            VideoPrivacyProfile.FACE_REDACTED,
                            owner_user_id=1,
                        )
                    )
            with Session(self.database) as db:
                saved = db.exec(
                    select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == "VID-CLEANUP")
                ).one()
                self.assertEqual(saved.status, VideoPrivacyStatus.FAILED)
                self.assertEqual(saved.current_stage, "cleanup")
                self.assertEqual(saved.original_path, str(encrypted))
                self.assertFalse(saved.output_usable)

    def test_sweep_expires_ready_job_and_deletes_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(root=Path(directory))
            job_id = "VID-EXPIRED"
            job = VideoPrivacyJob(
                job_id=job_id,
                profile=VideoPrivacyProfile.FACE_REDACTED,
                display_label="Video upload 01",
                content_type="video/mp4",
                status=VideoPrivacyStatus.READY,
                output_usable=True,
                retention_expires_at=utc_now() - timedelta(seconds=1),
            )
            with Session(self.database) as db:
                db.add(job)
                db.commit()
            retained = Path(directory) / job_id / "retained"
            retained.mkdir(parents=True)
            retained.joinpath("video.output.mp4.enc").write_bytes(b"ciphertext")
            with patch.object(service, "engine", self.database), patch.object(
                service, "VideoStorage", return_value=storage
            ):
                service.sweep_video_privacy_jobs()
            with Session(self.database) as db:
                saved = db.exec(
                    select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)
                ).first()
                self.assertIsNotNone(saved)
                if saved is None:
                    self.fail("expired job was not persisted")
                self.assertEqual(saved.status, VideoPrivacyStatus.EXPIRED)
            self.assertFalse((Path(directory) / job_id).exists())

    def test_expired_processing_job_is_not_deleted_in_flight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(root=Path(directory))
            job_id = "VID-PROCESSING"
            work = Path(directory) / job_id / "work"
            work.mkdir(parents=True)
            marker = work / "input.mp4"
            marker.write_bytes(b"temporary")
            job = VideoPrivacyJob(
                job_id=job_id,
                profile=VideoPrivacyProfile.FACE_REDACTED,
                display_label="Video upload 01",
                content_type="video/mp4",
                status=VideoPrivacyStatus.PROCESSING,
                current_stage="privacy-transform",
                retention_expires_at=utc_now() - timedelta(seconds=1),
            )
            with Session(self.database) as db:
                result = service._expire_if_needed(db, job, storage)
            self.assertEqual(result.status, VideoPrivacyStatus.PROCESSING)
            self.assertTrue(marker.exists())

    def test_sweep_terminates_expired_active_privacy_job(self) -> None:
        """A job that exceeds retention is failed and its private work is removed."""
        with tempfile.TemporaryDirectory() as directory:
            storage = VideoStorage(root=Path(directory))
            job_id = "VID-EXPIRED-ACTIVE"
            work = Path(directory) / job_id / "work"
            work.mkdir(parents=True)
            marker = work / "input.mp4"
            marker.write_bytes(b"temporary")
            job = VideoPrivacyJob(
                job_id=job_id,
                profile=VideoPrivacyProfile.FACE_REDACTED,
                display_label="Video upload 01",
                content_type="video/mp4",
                status=VideoPrivacyStatus.PROCESSING,
                current_stage="privacy-transform",
                original_path=str(Path(directory) / job_id / "original" / "video.input.enc"),
                retention_expires_at=utc_now() - timedelta(seconds=1),
            )
            with Session(self.database) as db:
                db.add(job)
                db.commit()
            with patch.object(service, "engine", self.database), patch.object(
                service, "VideoStorage", return_value=storage
            ):
                service.sweep_video_privacy_jobs()
            with Session(self.database) as db:
                saved = db.exec(select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == job_id)).one()
                self.assertEqual(saved.status, VideoPrivacyStatus.FAILED)
                self.assertEqual(saved.current_stage, "retention-expired")
                self.assertIsNone(saved.original_path)
            self.assertFalse(marker.exists())

    def test_finalization_bounds_ffmpeg_and_ffprobe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            visual = Path(directory) / "visual.mp4"
            output = Path(directory) / "output.mp4"
            source.write_bytes(b"source")
            visual.write_bytes(b"visual")
            calls = []

            def run(command, **kwargs):
                calls.append({"command": command, **kwargs})
                if command[0] == "/usr/bin/ffmpeg":
                    output.write_bytes(b"output")
                    return subprocess.CompletedProcess(command, 0, b"", b"")
                return subprocess.CompletedProcess(
                    command,
                    0,
                    b'{"streams":[{"codec_type":"video"}],"format":{"tags":{}}}',
                    b"",
                )

            with patch.object(service.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"), patch.object(
                service.subprocess, "run", side_effect=run
            ):
                service.finalize_protected_video(source, visual, output)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call.get("timeout") is not None for call in calls))
            self.assertIn("-an", calls[0]["command"])
            self.assertNotIn("1:a:0?", calls[0]["command"])

    def test_cancelled_processing_is_terminal_and_cleans_private_work(self) -> None:
        """Cancellation cannot leave a privacy job looking runnable."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "VID-CANCEL-PROCESS" / "work" / "source.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            storage = VideoStorage(root=Path(directory))
            processor = service.VideoPrivacyProcessor()
            processor.process = lambda *_args, **_kwargs: (_ for _ in ()).throw(asyncio.CancelledError())
            job = VideoPrivacyJob(
                job_id="VID-CANCEL-PROCESS",
                profile=VideoPrivacyProfile.FACE_REDACTED,
                display_label="Video upload 01",
                content_type="video/mp4",
                status=VideoPrivacyStatus.QUEUED,
                original_path=str(Path(directory) / "VID-CANCEL-PROCESS" / "original" / "video.input.enc"),
                retention_expires_at=utc_now() + timedelta(hours=1),
            )
            with Session(self.database) as db:
                db.add(job)
                db.commit()
            storage.materialize_original = lambda *_args, **_kwargs: source

            with patch.object(service, "engine", self.database):
                with self.assertRaises(asyncio.CancelledError):
                    service._process_video_privacy_job(
                        "VID-CANCEL-PROCESS", storage=storage, processor=processor
                    )
            with Session(self.database) as db:
                saved = db.exec(select(VideoPrivacyJob).where(VideoPrivacyJob.job_id == "VID-CANCEL-PROCESS")).one()
                self.assertEqual(saved.status, VideoPrivacyStatus.FAILED)
                self.assertEqual(saved.current_stage, "interrupted")
                self.assertIsNone(saved.original_path)
                self.assertFalse(saved.output_usable)
            self.assertFalse(source.exists())

    def test_finalization_removes_oversized_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            visual = Path(directory) / "visual.mp4"
            output = Path(directory) / "output.mp4"
            source.write_bytes(b"source")
            visual.write_bytes(b"visual")

            def run(command, **_kwargs):
                if command[0] == "/usr/bin/ffmpeg":
                    output.write_bytes(b"too-large")
                return subprocess.CompletedProcess(command, 0, b'{"streams":[],"format":{}}', b"")

            with patch.object(service.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"), patch.object(
                service.subprocess, "run", side_effect=run
            ), patch.object(service, "VIDEO_MAX_OUTPUT_BYTES", 1, create=True):
                with self.assertRaises(VideoProcessorError):
                    service.finalize_protected_video(source, visual, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
