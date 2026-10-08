"""Owner source retention and reference playback, independent of model admission."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import io
from pathlib import Path
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
from sqlmodel import SQLModel, Session, create_engine
from starlette.datastructures import Headers

from backend.app.api import recordings, sessions, video_detection
from backend.app.core.security import require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.eeg import EEGSession, EEGRecording, AnalysisStatus, RecordingStatus
from backend.app.eeg.contracts import MODEL_CHANNELS
from backend.app.services import processing_service, video_detection_service
from backend.app.services.case_deletion_service import delete_case
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
        preview = self.client.get("/api/recordings/REC-SOURCE/signal?duration_seconds=2").json()
        self.assertEqual(preview["representation"], "original-source")
        self.assertEqual(len(preview["channels"]), 20)
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

    @unittest.skipUnless(__import__("cv2").__dict__.get("VideoCapture"), "OpenCV video runtime unavailable")
    def test_reference_video_without_pose_assets_can_play_download_and_reopen(self):
        video_bytes = Path("backend/tests/fixtures/synthetic-review.mp4").read_bytes()
        with Session(self.engine) as db, patch.object(video_detection_service, "load_contract", side_effect=AssertionError("must not load models")), patch.object(video_detection_service, "_preflight_uploaded_video", side_effect=AssertionError("must not run pose")):
            job = asyncio.run(video_detection_service.create_job(db, self.video,
                UploadFile(filename="source.mp4", file=io.BytesIO(video_bytes), headers=Headers({"content-type": "video/mp4"})),
                1, reference_only=True))
            job_id, case_id = job.job_id, job.case_id
        with patch.object(video_detection_service, "engine", self.engine), patch.object(video_detection_service, "VideoStorage", return_value=self.video), patch.object(video_detection_service, "execute", side_effect=AssertionError("must not run VSViG")):
            video_detection_service.process_job(job_id)
            video_detection_service.sweep(startup=True)
        response = self.client.get(f"/api/video-detection/jobs/{job_id}")
        job = response.json()["job"]
        self.assertEqual(job["status"], "ready", job)
        self.assertEqual(job["review_privacy_method"], "unblurred-owner-source")
        self.assertIsNone(job["retention_expires_at"])
        self.assertEqual(self.client.get(f"/api/video-detection/jobs/{job_id}/original").content, video_bytes)
        ranged = self.client.get(f"/api/video-detection/jobs/{job_id}/visualization", headers={"Range": "bytes=0-63"})
        self.assertEqual(ranged.status_code, 206)
        self.assertEqual(len(ranged.content), 64)
        self.user = User(id=2, public_id="USR-OTHER", email="other@example.test")
        for suffix in ("/original", "/visualization", "/predictions"):
            self.assertEqual(self.client.get(f"/api/video-detection/jobs/{job_id}{suffix}").status_code, 404)
        with Session(self.engine) as db:
            delete_case(db, case_id=case_id, owner_user_id=1, eeg_storage=self.storage, video_storage=self.video)
        self.assertFalse((self.storage.root / job_id).exists())


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
