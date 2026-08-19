"""Basic end-to-end checks using a small synthetic EDF fixture.

Run with: PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
"""

from datetime import datetime
import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import ANY, AsyncMock, patch

import numpy as np
import pyedflib
from fastapi import BackgroundTasks, UploadFile
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine

from backend.app.main import app
from backend.app.database.models.eeg import (
    AnalysisStatus,
    EEGRecording,
    EEGSession,
    Explanation,
    Prediction,
    ProcessingAttempt,
    ProcessingStage,
    ProcessingStatus,
    RecordingStatus,
)
from backend.app.database.repository import (
    get_recording_by_public_id,
    get_session_by_database_id,
    get_session_by_public_id,
    list_explanations,
    list_flagged_window_counts,
    list_predictions,
    list_recordings_for_session,
    list_sessions,
)
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.preprocessing import EEGPreprocessor
from backend.app.eeg.model_input import MODEL_CHANNELS, prepare_model_windows
from backend.app.ml.stub_inference import StubInferenceService
from backend.app.privacy.deidentify import deidentify_edf, generate_record_id, inspect_metadata
from backend.app.privacy.signal_projection import cancellable_signal_projection, psd_features
from backend.app.research.chb_mit import (
    seizure_window_labels,
    sidecar_annotations,
    sidecar_path,
    summary_annotations,
)
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.session_service import create_session, delete_session, public_record, public_session
from backend.app.services.validation_service import ValidationError, validate_edf


class BackendTests(unittest.TestCase):
    storage_key = b"s" * 32

    def _store_archive(self, storage: SessionStorage, session_id: str, archive: Path) -> Path:
        """Store a local ZIP through the same encrypted upload path as the API."""

        upload = UploadFile(filename=archive.name, file=io.BytesIO(archive.read_bytes()))
        return asyncio.run(storage.save_upload(session_id, upload))

    def _create_source_edf(
        self,
        path: Path,
        labels: tuple[str, ...] = ("FP1-F7", "F7-T7"),
        sample_count: int = 512,
    ) -> np.ndarray:
        samples = np.asarray(
            [np.arange(sample_count, dtype=np.int32) - sample_count // 2 + index for index in range(len(labels))]
        )
        headers = [
            {
                "label": label,
                "dimension": "uV",
                "sample_frequency": 256,
                "physical_min": -1000,
                "physical_max": 1000,
                "digital_min": -2048,
                "digital_max": 2047,
                "prefilter": "",
                "transducer": "",
            }
            for label in labels
        ]
        writer = pyedflib.EdfWriter(str(path), len(labels), file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            writer.setHeader({
                "technician": "Technician Name",
                "recording_additional": "Ward 2",
                "patientname": "Jane Doe",
                "patient_additional": "Address",
                "patientcode": "PATIENT-123",
                "equipment": "EEG Device",
                "admincode": "ADMIN-1",
                "sex": "F",
                "startdate": datetime(2025, 1, 1, 12, 0, 0),
                "birthdate": "01 jan 1990",
            })
            writer.setSignalHeaders(headers)
            writer.writeSamples(samples, digital=True)
            writer.writeAnnotation(1.0, 2.0, "Jane Doe seizure note")
        finally:
            writer.close()
        return samples

    def test_deidentification_preserves_eeg_and_sanitizes_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.edf", root / "anonymous.edf"
            original = self._create_source_edf(source)
            anonymous_id = generate_record_id()
            deidentify_edf(source, output, anonymous_id)

            self.assertTrue(output.exists())
            reader = pyedflib.EdfReader(str(output))
            try:
                copied = np.asarray([reader.readSignal(i, digital=True) for i in range(2)])
                self.assertTrue(np.array_equal(copied, original))
                self.assertEqual(reader.getSignalLabels(), ["FP1-F7", "F7-T7"])
                self.assertEqual(reader.getSampleFrequencies().tolist(), [256.0, 256.0])
                self.assertEqual(reader.getPatientName(), anonymous_id)
                self.assertEqual(reader.getPatientCode(), anonymous_id)
                self.assertEqual(reader.getTechnician(), "")
                self.assertEqual(reader.getEquipment(), "")
                self.assertEqual(reader.getBirthdate(), "")
                onsets, durations, descriptions = reader.readAnnotations()
                self.assertEqual(onsets.tolist(), [1.0])
                self.assertEqual(durations.tolist(), [2.0])
                self.assertEqual(descriptions.tolist(), [""])
            finally:
                reader.close()

            metadata = inspect_metadata(output)
            self.assertEqual(metadata["technical"]["number_of_channels"], 2)
            self.assertFalse(any(metadata["potential_identifiers_present"].values()))

    def test_preprocessing_preserves_shape_and_clips_values(self) -> None:
        data = np.vstack((np.sin(np.linspace(0, 20, 512)), np.zeros(512)))
        processed = EEGPreprocessor(sampling_rate=256).preprocess(data)
        self.assertEqual(processed.shape, data.shape)
        self.assertLessEqual(np.abs(processed).max(), 5)

    def test_model_windows_match_the_trained_input_contract(self) -> None:
        labels = list(MODEL_CHANNELS) + ["P7-T7", "T7-FT9", "FT9-FT10", "FT10-T8", "T8-P8"]
        signals = np.arange(23 * 2048, dtype=np.float64).reshape(23, 2048)
        windows, starts, discarded = prepare_model_windows(signals, 256, labels)

        self.assertEqual(windows.shape, (2, 1024, 18))
        self.assertEqual(windows.dtype, np.float32)
        self.assertEqual(starts.tolist(), [0.0, 4.0])
        self.assertEqual(discarded, 0)
        self.assertEqual(windows[0, 0, 0], signals[0, 0])
        self.assertEqual(windows[1, 0, 17], signals[17, 1024])

    def test_uniform_reader_reopens_edf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.edf"
            self._create_source_edf(source)
            data, frequency, labels = read_uniform_edf(source)
            self.assertEqual(data.shape, (2, 512))
            self.assertEqual(frequency, 256)
            self.assertEqual(labels, ["FP1-F7", "F7-T7"])

    def test_stub_predictions_are_deterministic_and_non_clinical_contract_is_stable(self) -> None:
        service = StubInferenceService()
        windows = np.arange(2 * 1024 * 18, dtype=np.float32).reshape(2, 1024, 18) / 1000
        starts = np.asarray([0.0, 4.0], dtype=np.float32)
        first = service.predict(windows, starts, "REC-TEST")
        second = service.predict(windows, starts, "REC-TEST")
        transformed = cancellable_signal_projection(windows, b"t" * 32)
        projected = service.predict(transformed, starts, "REC-TEST")
        self.assertEqual(first, second)
        self.assertNotEqual(first, projected)
        self.assertEqual(service.model_name, "development-stub")
        self.assertEqual(service.model_version, "stub-0.1.0")
        self.assertTrue(all(0 <= item.probability <= 1 for item in first))

    def test_h5_runtime_fails_closed_without_a_reviewed_contract(self) -> None:
        from backend.app.ml.h5_inference import H5InferenceService, H5ModelError

        with self.assertRaises(H5ModelError):
            H5InferenceService(Path("missing-model.h5"), Path("missing-contract.json"))

    def test_storage_rejects_archive_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions")
            archive = Path(directory) / "unsafe.zip"
            import zipfile

            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.edf", b"not an EDF")
            with self.assertRaises(StorageError):
                storage.extract_edfs("SES-TEST", archive)

    def test_storage_ignores_hidden_macos_edf_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions")
            archive = Path(directory) / "macos.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("chb01/chb01_01.edf", b"real")
                output.writestr("__MACOSX/chb01/._chb01_01.edf", b"apple-double")
                output.writestr("chb01/.hidden.edf", b"hidden")

            extracted = storage.extract_edfs("SES-MACOS", archive)

            self.assertEqual([path.name for path in extracted], ["chb01_01.edf"])

    def test_storage_encrypts_uploads_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = SessionStorage(root / "sessions", self.storage_key)
            payload = b"PK\x03\x04encrypted archive bytes"
            archive = asyncio.run(
                storage.save_upload("SES-CRYPTO", UploadFile(filename="session.zip", file=io.BytesIO(payload)))
            )
            self.assertNotIn(payload, archive.read_bytes())
            self.assertEqual(storage.materialize_archive("SES-CRYPTO", archive).read_bytes(), payload)
            with archive.open("r+b") as output:
                output.seek(24)
                original_byte = output.read(1)
                output.seek(24)
                output.write(bytes([original_byte[0] ^ 0xFF]))
            with self.assertRaises(StorageError):
                storage.materialize_archive("SES-CRYPTO", archive)

    def test_cancellable_signal_projection_is_keyed_lossy_and_model_compatible(self) -> None:
        windows = np.random.default_rng(42).normal(size=(2, 1024, 18)).astype(np.float32)
        first = cancellable_signal_projection(windows, b"a" * 32)
        second = cancellable_signal_projection(windows, b"a" * 32)
        rotated = cancellable_signal_projection(windows, b"b" * 32)
        features = psd_features(first)
        self.assertEqual(features.shape, (2, 90))
        self.assertEqual(first.shape, (2, 1024, 18))
        self.assertEqual(first.dtype, np.float32)
        self.assertTrue(np.array_equal(first, second))
        self.assertFalse(np.array_equal(first, rotated))
        self.assertFalse(np.array_equal(first, windows))

    def test_openapi_contains_only_current_routes(self) -> None:
        schema = app.openapi()
        paths = set(schema["paths"])
        self.assertNotIn("/api/v1/deidentify", paths)
        self.assertNotIn("/api/v1/preprocess/{session_id}", paths)
        self.assertIn("/api/sessions/upload", paths)
        self.assertIn("/api/recordings/{record_id}/prediction", paths)
        self.assertNotIn("patient_reference", str(schema))

    def test_status_and_stage_columns_use_varchar_enum_processing(self) -> None:
        columns = (
            EEGSession.__table__.c.status,
            EEGRecording.__table__.c.status,
            ProcessingAttempt.__table__.c.stage,
            ProcessingAttempt.__table__.c.status,
        )
        for column in columns:
            self.assertFalse(column.type.native_enum)

    def test_failed_transaction_can_mark_session_failed_and_cleanup_storage(self) -> None:
        from backend.app.services.processing_service import _mark_session_failed

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            session_dir = storage.session_dir("SES-DB-FAIL")
            (session_dir / "original").mkdir()
            (session_dir / "original" / "upload.zip.enc").write_bytes(b"private")
            with Session(engine) as db:
                db.add(EEGSession(session_id="SES-DB-FAIL"))
                db.commit()
                db.add(EEGSession(session_id="SES-DB-FAIL"))
                with self.assertRaises(IntegrityError):
                    db.commit()

                _mark_session_failed(db, "SES-DB-FAIL", "Processing failed unexpectedly.")
                failed = get_session_by_public_id(db, "SES-DB-FAIL")
                self.assertEqual(failed.status, AnalysisStatus.FAILED)
                self.assertEqual(failed.error_message, "Processing failed unexpectedly.")
                self.assertIsNotNone(failed.completed_at)

                db.rollback()
                storage.cleanup_session("SES-DB-FAIL")
                self.assertFalse(session_dir.exists())

    def test_delete_preflight_is_allowed_from_local_frontend(self) -> None:
        messages: list[dict[str, object]] = []
        request = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "OPTIONS",
            "scheme": "http",
            "path": "/api/sessions/SES-NOT-REAL",
            "raw_path": b"/api/sessions/SES-NOT-REAL",
            "query_string": b"",
            "headers": [
                (b"origin", b"http://localhost:3000"),
                (b"access-control-request-method", b"DELETE"),
                (b"access-control-request-headers", b"accept"),
            ],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 8000),
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        asyncio.run(app(request, receive, send))
        response = next(message for message in messages if message["type"] == "http.response.start")
        headers = dict(response["headers"])  # type: ignore[arg-type]
        self.assertEqual(response["status"], 200)
        self.assertIn(b"DELETE", headers[b"access-control-allow-methods"])

    def test_chb_mit_window_labels_and_sidecar_name_are_deterministic(self) -> None:
        recording = Path("chb01_03.edf")
        self.assertEqual(sidecar_path(recording).name, "chb01_03.edf.seizures")
        self.assertEqual(seizure_window_labels([0.0, 4.0, 8.0], [(3.0, 6.0)]), [0, 1, 0])

    def test_chb_mit_summary_and_sidecar_annotations(self) -> None:
        summary = """File Name: chb01_01.edf
Number of Seizures in File: 0

File Name: chb01_03.edf
Number of Seizures in File: 1
Seizure Start Time: 2996 seconds
Seizure End Time: 3036 seconds
"""
        sidecar = bytes.fromhex(
            "005817fc23232074696d65207265736f6c7574696f6e3a2032353600"
            "00ecffffffff010000ec0b0000b4008000ec0000002800840000"
        )

        self.assertEqual(summary_annotations(summary)["chb01_01.edf"], [])
        self.assertEqual(summary_annotations(summary)["chb01_03.edf"], [(2996.0, 3036.0)])
        self.assertEqual(sidecar_annotations(sidecar), [(2996.0, 3036.0)])

    def test_upload_schedules_background_pipeline_without_rq_job_id(self) -> None:
        from backend.app.api.sessions import upload_session

        archive = UploadFile(filename="session.zip", file=io.BytesIO(b"zip"))
        session = EEGSession(
            session_id="SES-BACKGROUND",
            original_filename="session.zip",
            original_path="/private/session.zip",
            status=AnalysisStatus.QUEUED,
        )
        tasks = BackgroundTasks()

        with (
            patch("backend.app.api.sessions.create_session", new=AsyncMock(return_value=session)) as create,
            patch("backend.app.api.sessions.SessionStorage"),
            patch("backend.app.api.sessions.process_session") as process,
        ):
            payload = asyncio.run(upload_session(tasks, archive, "control"))

        self.assertEqual(payload, {"session_id": "SES-BACKGROUND", "status": "queued"})
        self.assertNotIn("job_id", payload)
        create.assert_awaited_once_with(
            ANY,
            ANY,
            archive,
            "control",
        )
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0].func, process)
        self.assertEqual(tasks.tasks[0].args, ("SES-BACKGROUND",))

    def test_upload_rejects_unimplemented_privacy_method(self) -> None:
        from backend.app.api.sessions import upload_session

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                upload_session(BackgroundTasks(), UploadFile(filename="session.zip", file=io.BytesIO(b"zip")), "differential-privacy")
            )
        self.assertEqual(raised.exception.status_code, 400)

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                upload_session(BackgroundTasks(), UploadFile(filename="session.zip", file=io.BytesIO(b"zip")), "cancellable-psd-template")
            )
        self.assertEqual(raised.exception.status_code, 400)

    def test_signal_endpoint_is_disabled_by_default(self) -> None:
        from backend.app.api.recordings import get_signal

        with self.assertRaises(HTTPException) as raised:
            get_signal("REC-NOT-LOOKED-UP", db=None)
        self.assertEqual(raised.exception.status_code, 404)

    def test_signal_endpoint_returns_ten_seconds_of_model_channels(self) -> None:
        from backend.app.api.recordings import get_signal

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "preview.edf"
            self._create_source_edf(source, MODEL_CHANNELS, 2560)
            database = create_engine("sqlite://", connect_args={"check_same_thread": False})
            self.addCleanup(database.dispose)
            SQLModel.metadata.create_all(database)
            with Session(database) as db:
                session = EEGSession(session_id="SES-SIGNAL")
                db.add(session)
                db.commit()
                db.refresh(session)
                db.add(EEGRecording(record_id="REC-SIGNAL", session_db_id=session.id, sequence_index=1, original_filename="", deidentified_path=str(source), status=RecordingStatus.INFERRED))
                db.commit()

                with patch("backend.app.api.recordings.ENABLE_SIGNAL_PREVIEW", True):
                    payload = get_signal("REC-SIGNAL", 0, 10, 600, db)

            self.assertEqual(payload["duration_seconds"], 10)
            self.assertEqual(payload["channel_labels"], list(MODEL_CHANNELS))
            self.assertEqual(len(payload["samples"]), 18)
            self.assertEqual(len(payload["samples"][0]), 600)

    def test_prototype_has_no_redis_rq_or_worker_configuration(self) -> None:
        from backend.app.core import config

        compose = Path("docker-compose.yml").read_text(encoding="utf-8")
        requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")
        self.assertFalse(hasattr(config, "REDIS_URL"))
        self.assertFalse(hasattr(config, "RQ_QUEUE_NAME"))
        self.assertNotIn("\n  redis:\n", compose)
        self.assertNotIn("\n  worker:\n", compose)
        self.assertNotIn("redis", requirements)
        self.assertNotIn("rq", requirements)

    def test_validation_rejects_corrupt_edf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupt.edf"
            path.write_bytes(b"not an EDF")
            with self.assertRaises(ValidationError):
                validate_edf(path)

    def test_public_record_hides_submitted_filename(self) -> None:
        record = EEGRecording(
            record_id="REC-TEST",
            session_db_id=1,
            sequence_index=1,
            original_filename="Jane-Doe-Identifiable.edf",
            reference_annotation_source="chb-mit-summary",
            reference_intervals_json="[]",
            status=RecordingStatus.DEIDENTIFIED,
        )
        payload = public_record(record)
        self.assertEqual(payload["source_filename"], "recording_01.edf")
        self.assertEqual(payload["reference_annotation"], {"source": "chb-mit-summary", "intervals": []})
        self.assertNotIn("Jane", str(payload))

    def test_direct_recording_response_includes_safe_session_context(self) -> None:
        from backend.app.api.recordings import get_recording

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-RECORD-CONTEXT",
                privacy_method="control",
                original_filename="patient-upload.zip",
                original_path="/private/patient-upload.zip",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-RECORD-CONTEXT",
                session_db_id=session.id,
                sequence_index=12,
                original_filename="patient-name.edf",
                status=RecordingStatus.INFERRED,
            )
            db.add(record)
            db.commit()

            payload = get_recording(record.record_id, db)

        self.assertEqual(payload["session_id"], "SES-RECORD-CONTEXT")
        self.assertEqual(payload["privacy_method"], "control")
        self.assertIn("session_created_at", payload)
        self.assertEqual(payload["source_filename"], "recording_12.edf")
        self.assertNotIn("patient", str(payload).lower())

    def test_repositories_query_sessions_recordings_and_predictions(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-REPOSITORY",
                original_filename="upload.zip",
                original_path="/private/upload.zip",
                status=AnalysisStatus.COMPLETED,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-REPOSITORY",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="recording.edf",
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            self.assertEqual(get_session_by_public_id(db, "SES-REPOSITORY").session_id, "SES-REPOSITORY")
            self.assertEqual(get_session_by_database_id(db, session.id).session_id, "SES-REPOSITORY")
            self.assertEqual(len(list_sessions(db)), 1)
            self.assertEqual(list_recordings_for_session(db, session.id)[0].record_id, "REC-REPOSITORY")
            self.assertEqual(list_predictions(db, record.id), [])

    def test_public_session_reports_progress_and_model_alert_summary(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(session_id="SES-SUMMARY", status=AnalysisStatus.COMPLETED_WITH_ERRORS)
            db.add(session)
            db.commit()
            db.refresh(session)
            completed = EEGRecording(
                record_id="REC-SUMMARY-1",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="private-1.edf",
                status=RecordingStatus.INFERRED,
                reference_annotation_source="chb-mit-summary",
                reference_intervals_json="[[12, 24]]",
            )
            failed = EEGRecording(
                record_id="REC-SUMMARY-2",
                session_db_id=session.id,
                sequence_index=2,
                original_filename="private-2.edf",
                status=RecordingStatus.FAILED,
            )
            db.add(completed)
            db.add(failed)
            db.commit()
            db.refresh(completed)
            db.add(Prediction(
                recording_db_id=completed.id,
                window_index=0,
                model_name="development-stub",
                model_version="stub-0.1.0",
                probability=0.9,
                seizure_detected=True,
                start_seconds=0,
                end_seconds=4,
            ))
            db.commit()

            payload = public_session(db, session)
            flagged_counts = list_flagged_window_counts(db, [completed.id])

        self.assertEqual(payload["progress"], {
            "total_recordings": 2,
            "finished_recordings": 2,
            "completed_recordings": 1,
            "failed_recordings": 1,
            "percent": 100,
        })
        self.assertEqual(payload["summary"], {"dataset_seizure_recordings": 1, "model_alert_recordings": 1})
        self.assertEqual(payload["recordings"][0]["model_alert_window_count"], 1)
        self.assertEqual(flagged_counts, {completed.id: 1})

    def test_delete_session_removes_results_and_private_storage(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            session_dir = storage.session_dir("SES-DELETE")
            (session_dir / "original.zip").write_bytes(b"private")
            with Session(engine) as db:
                session = EEGSession(session_id="SES-DELETE", status=AnalysisStatus.COMPLETED)
                db.add(session)
                db.commit()
                db.refresh(session)
                record = EEGRecording(session_db_id=session.id, record_id="REC-DELETE", original_filename="private.edf")
                db.add(record)
                db.commit()
                db.refresh(record)
                db.add(Prediction(
                    recording_db_id=record.id,
                    window_index=0,
                    model_name="stub",
                    model_version="0.1",
                    probability=0.5,
                    seizure_detected=False,
                    start_seconds=0,
                    end_seconds=4,
                ))
                db.commit()
                db.refresh(record)

                delete_session(db, storage, session)
                self.assertIsNone(get_session_by_public_id(db, "SES-DELETE"))
                self.assertEqual(list_sessions(db), [])

            self.assertFalse((storage.root / "SES-DELETE").exists())

    def test_failed_upload_rolls_back_session_row(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        storage = SessionStorage(Path(tempfile.mkdtemp()) / "sessions")
        archive = UploadFile(filename="session.zip", file=io.BytesIO(b"zip"))

        with Session(engine) as db, patch.dict(os.environ, {"MDS01_STORAGE_KEY": ""}):
            with self.assertRaises(StorageError):
                asyncio.run(create_session(db, storage, archive))
            self.assertEqual(list_sessions(db), [])
            self.assertEqual(list(storage.root.iterdir()), [])

    def test_processing_attempt_records_completion(self) -> None:
        from backend.app.services.processing_service import _begin_attempt, _finish_attempt

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-ATTEMPT",
                original_filename="upload.zip",
                original_path="/private/upload.zip",
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            attempt = _begin_attempt(db, session, ProcessingStage.VALIDATION)
            _finish_attempt(db, attempt, ProcessingStatus.SUCCEEDED)
            db.refresh(attempt)

            self.assertEqual(attempt.status, ProcessingStatus.SUCCEEDED)
            self.assertIsNotNone(attempt.started_at)
            self.assertIsNotNone(attempt.finished_at)

    def test_processing_continues_after_one_recording_failure(self) -> None:
        from backend.app.services.processing_service import process_session

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "one.edf"
            second = root / "two.edf"
            self._create_source_edf(first)
            self._create_source_edf(second)
            archive = root / "session.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.write(first, first.name)
                output.write(second, second.name)
                output.writestr("__MACOSX/._one.edf", b"not an EDF")
                output.writestr(
                    "chb01-summary.txt",
                    "File Name: one.edf\nNumber of Seizures in File: 1\n"
                    "Seizure Start Time: 12 seconds\nSeizure End Time: 24 seconds\n\n"
                    "File Name: two.edf\nNumber of Seizures in File: 0\n",
                )

            database = create_engine("sqlite://", connect_args={"check_same_thread": False})
            self.addCleanup(database.dispose)
            SQLModel.metadata.create_all(database)
            storage = SessionStorage(root / "sessions", self.storage_key)
            encrypted_archive = self._store_archive(storage, "SES-PARTIAL", archive)
            with Session(database) as db:
                db.add(
                    EEGSession(
                        session_id="SES-PARTIAL",
                        original_filename="session.zip",
                        original_path=str(encrypted_archive),
                    )
                )
                db.commit()

            def process_record(db, session, record, storage, inference):
                if record.sequence_index == 1:
                    raise ValidationError("malformed EDF")
                record.status = RecordingStatus.INFERRED
                db.add(record)
                db.commit()

            with (
                patch("backend.app.services.processing_service.engine", database),
                patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
                patch("backend.app.services.processing_service._process_record", side_effect=process_record),
            ):
                process_session("SES-PARTIAL")

            with Session(database) as db:
                session = get_session_by_public_id(db, "SES-PARTIAL")
                records = list_recordings_for_session(db, session.id)
                self.assertEqual(session.status, AnalysisStatus.COMPLETED_WITH_ERRORS)
                self.assertEqual(len(records), 2)
                self.assertEqual(records[0].status, RecordingStatus.FAILED)
                self.assertEqual(records[1].status, RecordingStatus.INFERRED)
                self.assertEqual(records[0].error_message, "malformed EDF")
                self.assertEqual(records[0].reference_annotation_source, "chb-mit-summary")
                self.assertEqual(json.loads(records[0].reference_intervals_json), [[12.0, 24.0]])
                self.assertEqual(json.loads(records[1].reference_intervals_json), [])

    def test_full_pipeline_processes_a_model_compatible_edf(self) -> None:
        from backend.app.services.processing_service import process_session

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "model-compatible.edf"
            self._create_source_edf(source, MODEL_CHANNELS, 1024)
            archive = root / "session.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.write(source, source.name)

            database = create_engine("sqlite://", connect_args={"check_same_thread": False})
            self.addCleanup(database.dispose)
            SQLModel.metadata.create_all(database)
            storage = SessionStorage(root / "sessions", self.storage_key)
            encrypted_archive = self._store_archive(storage, "SES-FULL", archive)
            with Session(database) as db:
                db.add(
                    EEGSession(
                        session_id="SES-FULL",
                        privacy_method="cancellable-signal-projection",
                        original_filename="session.zip",
                        original_path=str(encrypted_archive),
                    )
                )
                db.commit()

            with (
                patch("backend.app.services.processing_service.engine", database),
                patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
                patch("backend.app.services.processing_service.read_base64_key", return_value=b"t" * 32),
            ):
                process_session("SES-FULL")

            with Session(database) as db:
                session = get_session_by_public_id(db, "SES-FULL")
                records = list_recordings_for_session(db, session.id)
                predictions = list_predictions(db, records[0].id)
                explanations = list_explanations(db, [prediction.id for prediction in predictions])
                self.assertEqual(session.status, AnalysisStatus.COMPLETED)
                self.assertEqual(session.privacy_method, "cancellable-signal-projection")
                self.assertEqual(records[0].status, RecordingStatus.INFERRED)
                self.assertEqual(len(predictions), 1)
                self.assertEqual(len(explanations), 1)
                self.assertEqual(session.original_path, "")
                self.assertIsNone(records[0].extracted_path)
                self.assertIsNone(records[0].deidentified_path)
                self.assertIsNone(records[0].preprocessed_path)
                self.assertFalse((storage.root / "SES-FULL").exists())

    def test_repository_lists_explanations(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-EXPLANATION",
                original_filename="upload.zip",
                original_path="/private/upload.zip",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(record_id="REC-EXPLANATION", session_db_id=session.id, original_filename="recording.edf")
            db.add(record)
            db.commit()
            db.refresh(record)
            prediction = Prediction(
                recording_db_id=record.id,
                window_index=0,
                model_name="stub",
                model_version="0.1",
                probability=0.5,
                seizure_detected=True,
                start_seconds=0,
                end_seconds=4,
            )
            db.add(prediction)
            db.commit()
            db.refresh(prediction)
            db.add(Explanation(prediction_db_id=prediction.id, method="stub", explanation_path="/private/explanation.json"))
            db.commit()

            self.assertEqual(len(list_explanations(db, [prediction.id])), 1)
            self.assertEqual(list_explanations(db, []), [])

if __name__ == "__main__":
    unittest.main()
