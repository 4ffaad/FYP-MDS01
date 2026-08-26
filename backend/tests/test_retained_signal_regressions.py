"""Regression checks for retained EEG artifact reconstruction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch

import numpy as np
import pyedflib
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database.models.eeg import (
    AnalysisStatus,
    EEGRecording,
    EEGSession,
    Prediction,
    RecordingStatus,
)
from backend.app.eeg.model_input import MODEL_CHANNELS, MODEL_SAMPLING_RATE
from backend.app.privacy.retention import write_obfuscated_npz, write_scrubbed_edf_clip
from backend.app.services.signal_service import build_signal_preview
from backend.app.services.storage_service import SessionStorage


class RetainedSignalRegressionTests(unittest.TestCase):
    """Protect retained previews against overlap and calibration regressions."""

    def test_obfuscated_overlap_is_stitched_once_in_source_time(self) -> None:
        """Overlapping model windows produce one monotonic sample timeline."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = SessionStorage(root / "sessions", b"s" * 32)
            artifact = root / "retained.npz"
            starts = np.asarray([0.0, 2.0, 4.0], dtype=np.float32)
            windows = np.empty((3, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
            for index, start in enumerate(starts):
                source_indexes = int(start * MODEL_SAMPLING_RATE) + np.arange(1024)
                windows[index] = np.repeat(source_indexes[:, None], len(MODEL_CHANNELS), axis=1)
            write_obfuscated_npz(artifact, windows, starts, np.arange(3))
            encrypted = storage.store_encrypted_artifact("SES-OVERLAP", artifact, "REC-OVERLAP.npz")

            engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
            self.addCleanup(engine.dispose)
            SQLModel.metadata.create_all(engine)
            with Session(engine) as db:
                session = EEGSession(session_id="SES-OVERLAP", status=AnalysisStatus.COMPLETED)
                db.add(session)
                db.commit()
                db.refresh(session)
                record = EEGRecording(
                    record_id="REC-OVERLAP",
                    session_db_id=session.id,
                    sequence_index=1,
                    original_filename="",
                    duration_seconds=8,
                    status=RecordingStatus.INFERRED,
                    retained_artifact_path=str(encrypted),
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                db.add(Prediction(
                    recording_db_id=record.id,
                    window_index=1,
                    model_name="test-model",
                    model_version="1",
                    probability=0.9,
                    seizure_detected=True,
                    start_seconds=2,
                    end_seconds=6,
                ))
                db.commit()

                with (
                    patch("backend.app.services.signal_service.ENABLE_SIGNAL_PREVIEW", True),
                    patch("backend.app.services.signal_service.ENABLE_FULL_SIGNAL_PREVIEW", False),
                ):
                    preview = build_signal_preview(db, session, record, storage, 0, 8, 4096)

            times = np.asarray(preview["time_seconds"])
            samples = np.asarray(preview["channels"][0]["samples"])
            self.assertEqual(len(times), 8 * MODEL_SAMPLING_RATE)
            self.assertTrue(np.all(np.diff(times) > 0))
            np.testing.assert_array_equal(samples, np.arange(8 * MODEL_SAMPLING_RATE))

    def test_scrubbed_edf_clip_preserves_physical_waveform(self) -> None:
        """A retained EDF keeps source calibration while removing identifiers."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.edf"
            retained = root / "retained.edf"
            frequency = 256
            sample_count = 1024
            source_labels = [*MODEL_CHANNELS, "ECG", "VNS", "PHOTIC", "RESP", "EXTRA"]
            digital = np.vstack([
                (np.arange(sample_count, dtype=np.int32) + channel * 31) % 2048 - 1024
                for channel in range(len(source_labels))
            ])
            headers = [
                {
                    "label": label,
                    "dimension": "uV",
                    "sample_frequency": frequency,
                    "physical_min": -807.032,
                    "physical_max": 1037.948,
                    "digital_min": -2048,
                    "digital_max": 2047,
                    "prefilter": "0.5-100 Hz",
                    "transducer": "private device",
                }
                for label in source_labels
            ]
            writer = pyedflib.EdfWriter(str(source), len(source_labels), file_type=pyedflib.FILETYPE_EDFPLUS)
            try:
                writer.setHeader({
                    "technician": "Tech",
                    "recording_additional": "Ward",
                    "patientname": "Private Patient",
                    "patient_additional": "Private note",
                    "patientcode": "PRIVATE-123",
                    "equipment": "Device",
                    "admincode": "Admin",
                    "sex": "",
                    "startdate": datetime(2025, 1, 1),
                    "birthdate": "",
                })
                writer.setSignalHeaders(headers)
                writer.writeSamples(digital, digital=True)
                writer.writeAnnotation(0.75, 0.5, "Private annotation")
            finally:
                writer.close()

            intervals = [(0.5, 1.5), (2.5, 3.5)]
            source_reader = pyedflib.EdfReader(str(source))
            try:
                expected = np.vstack([
                    np.concatenate([
                        source_reader.readSignal(channel, start=round(start * frequency), n=round((end - start) * frequency))
                        for start, end in intervals
                    ])
                    for channel in range(len(MODEL_CHANNELS))
                ])
            finally:
                source_reader.close()

            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                write_scrubbed_edf_clip(source, retained, intervals)

            edf_warnings = [
                item for item in captured
                if "Physical minimum" in str(item.message) or "Physical maximum" in str(item.message)
            ]
            self.assertEqual(edf_warnings, [])
            retained_reader = pyedflib.EdfReader(str(retained))
            try:
                self.assertEqual(retained_reader.signals_in_file, len(MODEL_CHANNELS))
                self.assertEqual(retained_reader.getSignalLabels(), list(MODEL_CHANNELS))
                actual = np.vstack([retained_reader.readSignal(channel) for channel in range(len(MODEL_CHANNELS))])
                np.testing.assert_allclose(actual, expected, rtol=0, atol=0.5)
                self.assertEqual(retained_reader.getPatientCode(), "")
                self.assertEqual(retained_reader.getTechnician(), "")
                self.assertEqual(retained_reader.getEquipment(), "")
                self.assertEqual(retained_reader.getSignalHeader(0)["transducer"], "")
                self.assertEqual(retained_reader.getStartdatetime().year, 1970)
                self.assertEqual(retained_reader.readAnnotations()[2].tolist(), [""])
            finally:
                retained_reader.close()


if __name__ == "__main__":
    unittest.main()
