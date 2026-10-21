"""Owner source retention and reference playback, independent of model admission."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
import pyedflib
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select
from starlette.datastructures import Headers

from backend.app.api import recordings, sessions, video_detection
from backend.app.core.security import require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.clinical_access_event import ClinicalAccessEvent
from backend.app.database.models.eeg import EEGSession, EEGRecording, AnalysisStatus, RecordingStatus
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.eeg.contracts import MODEL_CHANNELS
from backend.app.services import processing_service, video_detection_service
from backend.app.services.case_deletion_service import (
    CaseDeletionInProgress,
    delete_case,
)
from backend.app.services.session_service import create_session
from backend.app.services.signal_service import build_signal_preview
from backend.app.services.storage_service import SessionStorage
from backend.app.services.video_storage_service import VideoStorage


class SecureOwnerReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.storage = SessionStorage(self.root / "sessions", storage_key=b"k" * 32)
        self.video = VideoStorage(self.storage.root, storage_key=b"k" * 32)
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.user = User(id=1, public_id="USR-OWNER", email="owner@example.test")
        with Session(self.engine) as db:
            db.add(self.user)
            db.add(User(id=2, public_id="USR-OTHER", email="other@example.test"))
            db.commit()
            db.refresh(self.user)
            db.expunge(self.user)
        self.app = FastAPI()
        for router in (recordings.router, sessions.router, video_detection.router):
            self.app.include_router(router)
        def database():
            with Session(self.engine) as db:
                yield db
        self.app.dependency_overrides[get_session] = database
        self.app.dependency_overrides[require_api_auth] = lambda: self.user
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        for target, value in (("backend.app.api.recordings.SessionStorage", self.storage),
                              ("backend.app.api.sessions.SessionStorage", self.storage),
                              ("backend.app.api.video_detection.VideoStorage", self.video)):
            mocked = patch(target, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)

    def source(self):
        path = self.root / "source.edf"
        labels = [*MODEL_CHANNELS, "ECG", "Extra EEG"]
        writer = pyedflib.EdfWriter(str(path), len(labels), file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            writer.setStartdatetime(datetime(2020, 1, 1))
            writer.setSignalHeaders([{"label": label, "dimension": "uV", "sample_frequency": 256,
                                      "physical_min": -1000, "physical_max": 1000,
                                      "digital_min": -32768, "digital_max": 32767} for label in labels])
            writer.writeSamples([np.sin(np.arange(2048) / 20) * 50 for _ in labels])
            writer.writeAnnotation(1, 1, "Synthetic source annotation")
        finally:
            writer.close()
        data = path.read_bytes()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip:
            zip.writestr("recording.edf", data)
            zip.writestr("source-report.doc", b"synthetic original report")
        with Session(self.engine) as db:
            session = asyncio.run(create_session(db, self.storage, UploadFile(filename="upload.zip", file=io.BytesIO(archive.getvalue())), owner_user_id=1))
            self.session_id, self.case_id = session.session_id, session.case_id
            session.status = AnalysisStatus.FAILED
            extracted = self.storage.directory(session.session_id, "extracted") / "source.edf"
            extracted.write_bytes(data)
            record = EEGRecording(record_id="REC-SOURCE", session_db_id=session.id, original_filename="", extracted_path=str(extracted))
            db.add(record)
            db.commit()
            # Inference failure must preserve exact originals and readable traces.
            with patch.object(processing_service, "validate_edf", side_effect=ValueError("invalid input")):
                with self.assertRaises(ValueError):
                    processing_service._process_record(db, session, record, self.storage, None)
            record.status = RecordingStatus.FAILED
            db.add(record)
            db.add(session)
            db.commit()
        return data, archive.getvalue()

    def test_owner_downloads_full_source_and_report_and_other_account_is_denied(self):
        original, archive = self.source()
        self.storage.cleanup_session(self.session_id, keep_retained=True, keep_original=True)
        response = self.client.get("/api/recordings/REC-SOURCE/original")
        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
        self.assertEqual(response.content, original)
        self.assertIn("no-store", response.headers["cache-control"])
        self.assertEqual(self.client.get(f"/api/sessions/{self.session_id}/original").content, archive)
        self.assertEqual(self.client.get(f"/api/sessions/{self.session_id}/original-report").content, b"synthetic original report")
        signal_response = self.client.get(
            "/api/recordings/REC-SOURCE/signal?duration_seconds=2",
            headers={"Accept-Encoding": "gzip"},
        )
        self.assertEqual(signal_response.headers.get("content-encoding"), "gzip")
        self.assertIn("accept-encoding", signal_response.headers.get("vary", "").lower())
        self.assertIn("no-store", signal_response.headers.get("cache-control", ""))
        preview = signal_response.json()
        self.assertEqual(preview["representation"], "original-source")
        self.assertEqual(len(preview["channels"]), 20)
        self.assertEqual(preview["sampling_rate"], 256)
        self.assertLess(
            max(abs(sample) for channel in preview["channels"] for sample in channel["samples"]),
            100e-6,
        )
        with Session(self.engine) as db:
            events = db.exec(
                select(ClinicalAccessEvent).order_by(ClinicalAccessEvent.id)
            ).all()
            self.assertEqual(
                [event.action for event in events],
                [
                    "recording_download",
                    "session_archive_download",
                    "session_report_download",
                    "waveform_view",
                ],
            )
            self.assertTrue(all(event.actor_user_id == 1 for event in events))
        encrypted = list((self.storage.root / self.session_id / "retained").glob("*.enc"))[0]
        self.assertNotIn(b"Synthetic source annotation", encrypted.read_bytes())
        self.assertEqual(list((self.storage.root / self.session_id / "work").glob("*")), [])
        self.user = User(id=2, public_id="USR-OTHER", email="other@example.test")
        for suffix in ("", "/signal", "/explanation", "/original"):
            self.assertEqual(self.client.get("/api/recordings/REC-SOURCE" + suffix).status_code, 404)
        self.assertEqual(self.client.get(f"/api/sessions/{self.session_id}/original").status_code, 404)

    def test_case_storage_deletion_waits_for_active_source_reads(self):
        self.source()
        started = threading.Event()
        def delete():
            started.set()
            self.storage.delete_session(self.session_id)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.storage.read_lease(self.session_id):
                future = pool.submit(delete)
                self.assertTrue(started.wait(timeout=1))
                time.sleep(0.05)
                self.assertFalse(future.done())
            future.result(timeout=2)
        self.assertFalse((self.storage.root / self.session_id).exists())

    def test_chunk_encrypted_media_supports_random_ranges_and_rejects_tampering(self):
        job_id = "VID-" + "A" * 32
        payload = bytes((index * 29) % 251 for index in range(170_123))
        encrypted = asyncio.run(
            self.storage.save_chunked_upload(
                job_id,
                UploadFile(
                    filename="clip.mp4",
                    file=io.BytesIO(payload),
                ),
                filename="video.input.enc",
                max_bytes=200_000,
                chunk_bytes=64 * 1024,
            )
        )
        ciphertext = encrypted.read_bytes()
        self.assertNotIn(payload[:128], ciphertext)
        self.assertEqual(self.storage.chunked_plaintext_size(encrypted), len(payload))
        selected = b"".join(self.storage.iter_decrypted_range(encrypted, 65_530, 131_090))
        self.assertEqual(selected, payload[65_530:131_091])
        suffix = b"".join(self.storage.iter_decrypted_range(encrypted, len(payload) - 73, len(payload) - 1))
        self.assertEqual(suffix, payload[-73:])

        # The second encrypted data record starts after the header and first
        # independently authenticated chunk. A modified tag must fail closed.
        from backend.app.services.storage_service import _CHUNKED_HEADER_BYTES

        tampered = bytearray(encrypted.read_bytes())
        second_record = _CHUNKED_HEADER_BYTES + 64 * 1024 + 12
        tampered[second_record + 64 * 1024] ^= 1
        encrypted.write_bytes(tampered)
        with self.assertRaises(Exception):
            b"".join(
                self.storage.iter_decrypted_range(
                    encrypted, 64 * 1024, 64 * 1024 + 32
                )
            )

    def test_parallel_waveforms_cleanup_restart_missing_artifact_and_case_deletion(self):
        self.source()
        with self.storage.read_lease(self.session_id):
            self.storage.cleanup_session(self.session_id, keep_retained=True, keep_original=True)
            self.assertTrue((self.storage.root / self.session_id / "extracted" / "source.edf").exists())
        with patch.object(processing_service, "engine", self.engine), patch.object(processing_service, "SessionStorage", return_value=self.storage):
            processing_service.sweep_interrupted_sessions()
        with Session(self.engine) as db:
            session = db.get(EEGSession, 1)
            record = db.get(EEGRecording, 1)
            with ThreadPoolExecutor(max_workers=2) as pool:
                previews = list(pool.map(lambda start: build_signal_preview(db, session, record, self.storage, start, 1, 128), [0, 2]))
            self.assertEqual([len(item["channels"]) for item in previews], [20, 20])
            self.assertTrue(Path(session.original_path).is_file())
            Path(record.original_artifact_path).unlink()
        self.assertEqual(self.client.get("/api/recordings/REC-SOURCE/original").status_code, 404)
        with Session(self.engine) as db:
            delete_case(db, case_id=self.case_id, owner_user_id=1, eeg_storage=self.storage, video_storage=self.video)
            self.assertIsNone(db.get(EEGSession, 1))
        self.assertFalse((self.storage.root / self.session_id).exists())

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe video metadata probe unavailable")
    def test_reference_video_upload_acknowledges_before_probe_then_streams_authenticated_ranges(self):
        enabled_service = patch.object(video_detection_service, "CLINICAL_VIDEO_REVIEW_ENABLED", True)
        enabled_api = patch.object(video_detection, "CLINICAL_VIDEO_REVIEW_ENABLED", True)
        enabled_service.start()
        enabled_api.start()
        self.addCleanup(enabled_service.stop)
        self.addCleanup(enabled_api.stop)
        video_bytes = Path("backend/tests/fixtures/synthetic-review.mp4").read_bytes()
        with Session(self.engine) as db, patch.object(video_detection_service, "load_contract", side_effect=AssertionError("must not load models")), patch.object(video_detection_service, "_preflight_uploaded_video", side_effect=AssertionError("must not run pose")), patch.object(video_detection_service, "process_job", side_effect=AssertionError("reference upload must not enter the model worker")):
            job = asyncio.run(video_detection_service.create_job(db, self.video,
                UploadFile(filename="source.mp4", file=io.BytesIO(video_bytes), headers=Headers({"content-type": "video/mp4"})),
                1, reference_only=True))
            job_id, case_id = job.job_id, job.case_id
            self.assertEqual(job.status, "ready")
            self.assertEqual(job.playback_status, "metadata_pending")
            self.assertIsNone(job.playback_path)
            self.assertEqual(job.duration_seconds, 0.0)
        with patch.object(video_detection_service, "engine", self.engine), patch.object(
            video_detection_service, "VideoStorage", return_value=self.video
        ):
            video_detection_service.process_reference_metadata(job_id)
        with patch.object(video_detection_service, "engine", self.engine), patch.object(video_detection_service, "VideoStorage", return_value=self.video), patch.object(video_detection_service, "execute", side_effect=AssertionError("must not run VSViG")):
            video_detection_service.process_reference_metadata(job_id)
            video_detection_service.sweep(startup=True)
        response = self.client.get(f"/api/video-detection/jobs/{job_id}")
        job = response.json()["job"]
        self.assertEqual(job["status"], "ready", job)
        self.assertEqual(job["review_privacy_method"], "unblurred-owner-source")
        self.assertIsNone(job["retention_expires_at"])
        self.assertEqual(job["retention_policy"], "until-deletion")
        self.assertEqual(job["video_access_status"], "available")
        self.assertEqual(job["playback_status"], "direct")
        self.assertTrue(job["source_download_available"])
        self.assertEqual(self.client.get(f"/api/video-detection/jobs/{job_id}/original").content, video_bytes)
        ranged = self.client.get(f"/api/video-detection/jobs/{job_id}/playback", headers={"Range": "bytes=0-63"})
        self.assertEqual(ranged.status_code, 206)
        self.assertEqual(len(ranged.content), 64)
        self.assertEqual(ranged.headers.get("cache-control"), "private, no-store, max-age=0")
        self.assertEqual(ranged.headers.get("content-range"), f"bytes 0-63/{len(video_bytes)}")
        self.user = User(id=2, public_id="USR-OTHER", email="other@example.test")
        for suffix in ("/original", "/playback", "/visualization", "/predictions"):
            self.assertEqual(self.client.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 404)
        with Session(self.engine) as db:
            delete_case(db, case_id=case_id, owner_user_id=1, eeg_storage=self.storage, video_storage=self.video)
        self.assertFalse((self.storage.root / job_id).exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg video tooling unavailable")
    def test_unsupported_reference_is_prepared_in_background_after_upload(self):
        service_review = patch.object(video_detection_service, "CLINICAL_VIDEO_REVIEW_ENABLED", True)
        api_review = patch.object(video_detection, "CLINICAL_VIDEO_REVIEW_ENABLED", True)
        service_review.start()
        api_review.start()
        self.addCleanup(service_review.stop)
        self.addCleanup(api_review.stop)
        source = self.root / "unsupported-reference.avi"
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-v", "error", "-f", "lavfi", "-i",
                "testsrc2=size=96x64:rate=6", "-frames:v", "24",
                "-an", "-c:v", "mpeg4", "-y", str(source),
            ],
            check=True,
            timeout=30,
        )
        source_bytes = source.read_bytes()
        with Session(self.engine) as db:
            job = asyncio.run(
                video_detection_service.create_job(
                    db,
                    self.video,
                    UploadFile(
                        filename="source.avi",
                        file=io.BytesIO(source_bytes),
                        headers=Headers({"content-type": "video/x-msvideo"}),
                    ),
                    1,
                    reference_only=True,
                )
            )
            job_id = job.job_id
            case_id = job.case_id
            self.assertEqual(job.status, "ready")
            self.assertEqual(job.playback_status, "metadata_pending")
            self.assertIsNone(job.playback_path)

        retained_original = Path(job.original_path or "")
        self.assertTrue(retained_original.is_file())
        self.assertNotIn(source_bytes, retained_original.read_bytes())
        with patch.object(video_detection_service, "engine", self.engine), patch.object(
            video_detection_service, "VideoStorage", return_value=self.video
        ), patch.object(video_detection_service, "enqueue_reference_playback") as enqueue_playback:
            video_detection_service.process_reference_metadata(job_id)
            enqueue_playback.assert_called_once_with(job_id)

        metadata_ready = self.client.get(f"/api/video-detection/jobs/{job_id}").json()["job"]
        self.assertEqual(metadata_ready["playback_status"], "processing")
        with patch.object(
            video_detection_service,
            "prioritize_reference_playback",
        ) as enqueue_playback:
            response = self.client.post(f"/api/video-detection/jobs/{job_id}/playback")
        self.assertEqual(response.status_code, 202, response.text)
        enqueue_playback.assert_called_once_with(job_id)
        self.assertEqual(
            self.client.get(f"/api/video-detection/jobs/{job_id}").json()["job"]["playback_status"],
            "processing",
        )
        with patch.object(video_detection_service, "engine", self.engine), patch.object(
            video_detection_service, "VideoStorage", return_value=self.video
        ):
            video_detection_service.process_reference_playback(job_id)
        prepared = self.client.get(f"/api/video-detection/jobs/{job_id}").json()["job"]
        self.assertEqual(prepared["playback_status"], "ready", prepared)
        self.assertTrue(prepared["video_available"])
        playback_path = Path(prepared["playback_path"]) if "playback_path" in prepared else self.video.playback_path(job_id)
        self.assertTrue(playback_path.is_file())
        self.assertNotIn(b"ftyp", playback_path.read_bytes()[:64])
        self.assertTrue(retained_original.is_file())
        ranged = self.client.get(
            f"/api/video-detection/jobs/{job_id}/playback",
            headers={"Range": "bytes=0-31"},
        )
        self.assertEqual(ranged.status_code, 206, ranged.text)
        self.assertEqual(len(ranged.content), 32)
        self.assertEqual(ranged.headers.get("cache-control"), "private, no-store, max-age=0")
        first_mtime = playback_path.stat().st_mtime_ns
        repeated = self.client.post(f"/api/video-detection/jobs/{job_id}/playback")
        self.assertEqual(repeated.status_code, 202, repeated.text)
        self.assertEqual(playback_path.stat().st_mtime_ns, first_mtime)
        cache_path = self.video.root / job_id / "work" / "reference-playback-cache.mp4"
        self.assertFalse(cache_path.exists())
        self.user = User(id=2, public_id="USR-OTHER", email="other@example.test")
        self.assertEqual(self.client.get(f"/api/video-detection/jobs/{job_id}/playback").status_code, 404)
        self.assertEqual(self.client.post(f"/api/video-detection/jobs/{job_id}/playback").status_code, 404)
        self.user = User(id=1, public_id="USR-OWNER", email="owner@example.test")
        self.video.cleanup_stale_playback(job_id, now=time.time() + 11 * 60)
        self.assertFalse(cache_path.exists())
        with Session(self.engine) as db:
            delete_case(db, case_id=case_id, owner_user_id=1, eeg_storage=self.storage, video_storage=self.video)
        self.assertFalse((self.video.root / job_id).exists())

    def test_case_deletion_waits_for_on_demand_reference_conversion(self):
        job_id = "VID-ACTIVE-PLAYBACK-CONVERSION"
        case_id = "CASE-A17E0001"
        encrypted_original = self.video.root / job_id / "original" / "video.input.enc"
        encrypted_original.parent.mkdir(parents=True)
        encrypted_original.write_bytes(b"encrypted original")
        with Session(self.engine) as db:
            db.add(
                VideoDetectionJob(
                    owner_user_id=1,
                    case_id=case_id,
                    job_id=job_id,
                    status="ready",
                    reference_only=True,
                    playback_status="processing",
                    original_path=str(encrypted_original),
                )
            )
            db.commit()
            with self.assertRaises(CaseDeletionInProgress):
                delete_case(
                    db,
                    case_id=case_id,
                    owner_user_id=1,
                    eeg_storage=self.storage,
                    video_storage=self.video,
                )
        self.assertTrue(encrypted_original.is_file())

    def test_reference_conversion_claim_is_owner_scoped_and_idempotent(self):
        with Session(self.engine) as db:
            job = VideoDetectionJob(
                owner_user_id=1,
                case_id="CASE-PLAYBACK-CLAIM",
                job_id="VID-PLAYBACK-CLAIM",
                status="ready",
                reference_only=True,
                playback_status="conversion_required",
            )
            db.add(job)
            db.commit()

            claimed_job, claimed = video_detection_service.request_reference_playback(
                db, job.job_id, 1
            )
            self.assertTrue(claimed)
            self.assertEqual(claimed_job.playback_status, "processing")
            repeated_job, repeated_claim = (
                video_detection_service.request_reference_playback(db, job.job_id, 1)
            )
            self.assertFalse(repeated_claim)
            self.assertEqual(repeated_job.playback_status, "processing")

    def test_opened_reference_clip_is_promoted_ahead_of_background_queue(self):
        background_started = threading.Event()
        release_background = threading.Event()
        background_finished = threading.Event()
        priority_finished = threading.Event()
        order = []

        def fake_process(job_id):
            if job_id == "VID-BACKGROUND-RUNNING":
                background_started.set()
                release_background.wait(timeout=5)
                order.append(job_id)
                background_finished.set()
            else:
                order.append(job_id)
                priority_finished.set()

        background_executor = ThreadPoolExecutor(max_workers=1)
        priority_executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(background_executor.shutdown, wait=True)
        self.addCleanup(priority_executor.shutdown, wait=True)
        with patch.object(
            video_detection_service,
            "REFERENCE_PLAYBACK_EXECUTOR",
            background_executor,
        ), patch.object(
            video_detection_service,
            "REFERENCE_PLAYBACK_PRIORITY_EXECUTOR",
            priority_executor,
        ), patch.object(
            video_detection_service, "REFERENCE_PLAYBACK_SCHEDULE_LOCK", threading.Lock()
        ), patch.object(video_detection_service, "REFERENCE_PLAYBACK_FUTURES", {}), patch.object(
            video_detection_service, "REFERENCE_PLAYBACK_RUNNING", set()
        ), patch.object(
            video_detection_service, "process_reference_playback", side_effect=fake_process
        ):
            video_detection_service.enqueue_reference_playback("VID-BACKGROUND-RUNNING")
            self.assertTrue(background_started.wait(timeout=2))
            video_detection_service.enqueue_reference_playback("VID-OWNER-OPENED")
            video_detection_service.prioritize_reference_playback("VID-OWNER-OPENED")
            self.assertTrue(priority_finished.wait(timeout=2))
            self.assertEqual(order, ["VID-OWNER-OPENED"])
            release_background.set()
            self.assertTrue(background_finished.wait(timeout=2))

    def test_startup_requeues_interrupted_reference_playback_preparation(self):
        job_id = "VID-PLAYBACK-RECOVERY"
        original = self.video.root / job_id / "original" / "video.input.enc"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"encrypted source")
        with Session(self.engine) as db:
            db.add(
                VideoDetectionJob(
                    owner_user_id=1,
                    case_id="CASE-PLAYBACK-RECOVERY",
                    job_id=job_id,
                    status="ready",
                    reference_only=True,
                    playback_status="processing",
                    original_path=str(original),
                )
            )
            db.commit()

        with patch.object(video_detection_service, "engine", self.engine), patch.object(
            video_detection_service, "VideoStorage", return_value=self.video
        ), patch.object(
            video_detection_service, "enqueue_reference_playback"
        ) as enqueue_playback:
            video_detection_service.sweep(startup=True)

        enqueue_playback.assert_called_once_with(job_id)
        with Session(self.engine) as db:
            recovered = db.exec(
                select(VideoDetectionJob).where(VideoDetectionJob.job_id == job_id)
            ).one()
        self.assertEqual(recovered.playback_status, "processing")
        self.assertTrue(original.is_file())

    def test_unblurred_video_is_hidden_and_blocked_without_institutional_approval(self):
        job_id = "VID-UNAPPROVED-REVIEW"
        original = self.video.root / job_id / "original" / "video.input.enc"
        review = self.video.visualization_path(job_id)
        original.parent.mkdir(parents=True)
        review.parent.mkdir(parents=True)
        original.write_bytes(b"encrypted-source")
        review.write_bytes(b"encrypted-review")
        with Session(self.engine) as db:
            db.add(
                VideoDetectionJob(
                    owner_user_id=1,
                    job_id=job_id,
                    case_id="CASE-UNAPPROVED-REVIEW",
                    status="ready",
                    current_stage="reference-review-ready",
                    review_privacy_method="unblurred-owner-source",
                    reference_only=True,
                    original_path=str(original),
                    visualization_path=str(review),
                )
            )
            db.commit()

        detail = self.client.get(f"/api/video-detection/jobs/{job_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.json()["job"]["video_available"])
        self.assertEqual(detail.json()["job"]["video_access_status"], "review_disabled")
        self.assertTrue(detail.json()["job"]["source_available"])
        self.assertFalse(detail.json()["job"]["source_download_available"])
        for suffix in ("/original", "/visualization"):
            response = self.client.get(f"/api/video-detection/jobs/{job_id}{suffix}")
            self.assertEqual(response.status_code, 403)

        from backend.app.video_detection.contract import DetectionError
        with Session(self.engine) as db:
            with self.assertRaisesRegex(DetectionError, "clinical_video_review_disabled"):
                asyncio.run(
                    video_detection_service.create_job(
                        db,
                        self.video,
                        UploadFile(
                            filename="source.mp4",
                            file=io.BytesIO(b"unread video"),
                            headers=Headers({"content-type": "video/mp4"}),
                        ),
                        1,
                        reference_only=True,
                    )
                )


class SourceNicoletRangeTests(unittest.TestCase):
    def test_all_source_channels_and_native_rates_preserve_acquisition_gaps(self):
        from backend.app.eeg.legacy_nicolet import LegacyNicoletReader, NicoletHeader, NicoletChannel, NicoletSegment, _IndexEntry
        channels = tuple(NicoletChannel(label, 256, 1e-6, index) for index, label in enumerate([*MODEL_CHANNELS, "Extra EEG"]))
        channels += (NicoletChannel("ECG", 128, 1e-6, len(channels)),)
        stream = bytearray()
        entries = {}
        for channel in channels:
            count = 4 * channel.sampling_rate
            samples = np.concatenate([np.ones(count, dtype="<i2"), np.full(count, 101, dtype="<i2")])
            entries[channel.section_id] = (_IndexEntry(channel.section_id, len(stream), samples.nbytes),)
            stream.extend(samples.tobytes())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.e"
            path.write_bytes(b"synthetic source")
            reader = LegacyNicoletReader(path)
            reader._header = NicoletHeader(sampling_rate=256, channels=channels[:-1],
                segments=(NicoletSegment(0, 4, 1024, 0), NicoletSegment(10, 4, 1024, 1024)), total_samples=2048, events=())
            reader._section_entries = entries
            with patch.object(reader, "_open_source", side_effect=lambda: io.BytesIO(stream)), patch.object(reader, "_read_tags", return_value={}), patch.object(reader, "_read_ts_channels", return_value=list(channels)):
                payload = reader.read_source_range(3, 11, 1024)
            self.assertEqual(len(payload["channels"]), 20)
            self.assertEqual(payload["segments"], [{"source_start_seconds": 3, "source_end_seconds": 4}, {"source_start_seconds": 10, "source_end_seconds": 11}])
            ecg = payload["channels"][-1]
            self.assertEqual(ecg["sampling_rate"], 128)
            self.assertEqual(len(ecg["samples"]), 256)
            self.assertFalse(any(4 <= time < 10 for time in ecg["time_seconds"]))
            self.assertAlmostEqual(ecg["samples"][128], 101e-6)
