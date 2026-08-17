"""Basic end-to-end checks using a small synthetic EDF fixture.

Run with: PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
"""

from datetime import datetime
import asyncio
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np
import pyedflib
from fastapi import BackgroundTasks, UploadFile
from sqlmodel import Session, SQLModel, create_engine

from backend.app.main import app
from backend.app.database.models.eeg import AnalysisStatus, EEGRecording, EEGSession, RecordingStatus
from backend.app.database.repositories.recording_repository import list_for_session, list_predictions
from backend.app.database.repositories.session_repository import get_by_public_id, list_sessions
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.preprocessing import EEGPreprocessor
from backend.app.eeg.model_input import MODEL_CHANNELS, prepare_model_windows
from backend.app.ml.stub_inference import StubInferenceService
from backend.app.privacy.deidentify import deidentify_edf, generate_record_id, inspect_metadata
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.session_service import public_record
from backend.app.services.validation_service import ValidationError, validate_edf


class BackendTests(unittest.TestCase):
    def _create_source_edf(self, path: Path) -> np.ndarray:
        samples = np.array([
            np.arange(512, dtype=np.int32) - 256,
            np.arange(512, dtype=np.int32) - 128,
        ])
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
            for label in ("FP1-F7", "F7-T7")
        ]
        writer = pyedflib.EdfWriter(str(path), 2, file_type=pyedflib.FILETYPE_EDFPLUS)
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
                self.assertEqual(reader.getBirthdate(), "")
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
        windows = np.zeros((2, 1024, 18), dtype=np.float32)
        starts = np.asarray([0.0, 4.0], dtype=np.float32)
        first = service.predict(windows, starts, "REC-TEST")
        second = service.predict(windows, starts, "REC-TEST")
        self.assertEqual(first, second)
        self.assertEqual(service.model_name, "development-stub")
        self.assertEqual(service.model_version, "stub-0.1.0")
        self.assertTrue(all(0 <= item.probability <= 1 for item in first))

    def test_storage_rejects_archive_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions")
            archive = Path(directory) / "unsafe.zip"
            import zipfile

            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.edf", b"not an EDF")
            with self.assertRaises(StorageError):
                storage.extract_edfs("SES-TEST", archive)

    def test_openapi_contains_only_current_routes(self) -> None:
        paths = set(app.openapi()["paths"])
        self.assertNotIn("/api/v1/deidentify", paths)
        self.assertNotIn("/api/v1/preprocess/{session_id}", paths)
        self.assertIn("/api/sessions/upload", paths)
        self.assertIn("/api/recordings/{record_id}/prediction", paths)

    def test_upload_schedules_background_pipeline_without_rq_job_id(self) -> None:
        from backend.app.api.sessions import upload_session

        archive = UploadFile(filename="session.zip", file=io.BytesIO(b"zip"))
        session = EEGSession(
            session_id="SES-BACKGROUND",
            patient_reference="internal",
            original_filename="session.zip",
            original_path="/private/session.zip",
            status=AnalysisStatus.QUEUED,
        )
        tasks = BackgroundTasks()

        with (
            patch("backend.app.api.sessions.create_session", new=AsyncMock(return_value=session)),
            patch("backend.app.api.sessions.SessionStorage"),
            patch("backend.app.api.sessions.process_session") as process,
        ):
            payload = asyncio.run(upload_session(tasks, archive, "internal"))

        self.assertEqual(payload, {"session_id": "SES-BACKGROUND", "status": "queued"})
        self.assertNotIn("job_id", payload)
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0].func, process)
        self.assertEqual(tasks.tasks[0].args, ("SES-BACKGROUND",))

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
            status=RecordingStatus.DEIDENTIFIED,
        )
        payload = public_record(record)
        self.assertEqual(payload["source_filename"], "recording_01.edf")
        self.assertNotIn("Jane", str(payload))

    def test_repositories_query_sessions_recordings_and_predictions(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-REPOSITORY",
                patient_reference="internal",
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

            self.assertEqual(get_by_public_id(db, "SES-REPOSITORY").session_id, "SES-REPOSITORY")
            self.assertEqual(len(list_sessions(db)), 1)
            self.assertEqual(list_for_session(db, session.id)[0].record_id, "REC-REPOSITORY")
            self.assertEqual(list_predictions(db, record.id), [])

if __name__ == "__main__":
    unittest.main()
