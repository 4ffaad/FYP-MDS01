"""Regression checks for retained EEG artifact reconstruction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import tempfile
import unittest
import warnings
from types import SimpleNamespace
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
from backend.app.privacy.retention import (
    write_model_window_npz,
    write_obfuscated_npz,
    write_scrubbed_edf_clip,
)
from backend.app.services.signal_service import (
    _filter_review_signal,
    _read_npz_preview,
    build_signal_preview,
)
from backend.app.services.storage_service import SessionStorage


class RetainedSignalRegressionTests(unittest.TestCase):
    """Protect retained previews against overlap and calibration regressions."""

    def test_review_filter_removes_50_hz_interference_without_erasing_eeg(self) -> None:
        times = np.arange(10 * MODEL_SAMPLING_RATE) / MODEL_SAMPLING_RATE
        eeg = np.sin(2 * np.pi * 10 * times)
        mains = np.sin(2 * np.pi * 50 * times)
        filtered = _filter_review_signal(eeg + mains)
        original_spectrum = np.abs(np.fft.rfft(eeg + mains))
        filtered_spectrum = np.abs(np.fft.rfft(filtered))
        frequencies = np.fft.rfftfreq(len(times), 1 / MODEL_SAMPLING_RATE)
        ten_hz = np.argmin(np.abs(frequencies - 10))
        fifty_hz = np.argmin(np.abs(frequencies - 50))
        self.assertGreater(filtered_spectrum[ten_hz] / original_spectrum[ten_hz], 0.8)
        self.assertLess(filtered_spectrum[fifty_hz] / original_spectrum[fifty_hz], 0.1)

    def test_parallel_waveform_ranges_materialize_to_distinct_private_files(self) -> None:
        """Concurrent chart range fetches must not share plaintext temp paths."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = SessionStorage(root / "sessions", b"s" * 32)
            source = root / "retained.npz"
            windows = np.zeros((1, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
            write_model_window_npz(source, windows, np.asarray([0.0]), np.asarray([0]))
            encrypted = storage.store_encrypted_artifact("SES-PARALLEL", source, "REC-PARALLEL.npz")
            session = SimpleNamespace(session_id="SES-PARALLEL", privacy_method="metadata-scrub")
            record = SimpleNamespace(
                id=1,
                record_id="REC-PARALLEL",
                status=RecordingStatus.INFERRED,
                retained_artifact_path=str(encrypted),
                duration_seconds=4.0,
            )
            barrier = Barrier(2)
            paths: list[Path] = []

            def read_preview(path: Path, *_args, **_kwargs) -> dict:
                paths.append(path)
                barrier.wait(timeout=5)
                self.assertTrue(path.is_file())
                return {"channels": [], "time_seconds": [], "segments": []}

            with (
                patch("backend.app.services.signal_service.ENABLE_SIGNAL_PREVIEW", True),
                patch("backend.app.services.signal_service.ENABLE_FULL_SIGNAL_PREVIEW", True),
                patch("backend.app.services.signal_service.list_predictions", return_value=[]),
                patch("backend.app.services.signal_service._read_npz_preview", side_effect=read_preview),
                ThreadPoolExecutor(max_workers=2) as pool,
            ):
                futures = [
                    pool.submit(build_signal_preview, object(), session, record, storage, start, 2, 128)
                    for start in (0.0, 1.0)
                ]
                for future in futures:
                    future.result(timeout=10)

            self.assertEqual(len(paths), 2)
            self.assertEqual(len(set(paths)), 2)
            self.assertTrue(all(not path.exists() for path in paths))

    def test_gap_preserving_preview_filters_continuous_model_windows(self) -> None:
        starts = np.asarray([0.0, 2.0, 4.0, 6.0], dtype=np.float64)
        samples = np.arange(10 * MODEL_SAMPLING_RATE) / MODEL_SAMPLING_RATE
        source = np.sin(2 * np.pi * 10 * samples) + np.sin(2 * np.pi * 50 * samples)
        windows = np.stack([
            np.repeat(source[int(start * MODEL_SAMPLING_RATE):int(start * MODEL_SAMPLING_RATE) + 1024, None], len(MODEL_CHANNELS), axis=1)
            for start in starts
        ]).astype(np.float32)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "retained.npz"
            write_model_window_npz(artifact, windows, starts, np.arange(len(starts)))
            preview = _read_npz_preview(
                artifact, [], 0.0, 10.0, 10_000, filter_for_display=True
            )
        self.assertEqual(preview["display_filter"], "0.5–70 Hz · 50 Hz notch")
        self.assertEqual(len(preview["time_seconds"]), len(samples))
        spectrum = np.abs(np.fft.rfft(preview["channels"][0]["samples"]))
        frequencies = np.fft.rfftfreq(len(samples), 1 / MODEL_SAMPLING_RATE)
        self.assertGreater(spectrum[np.argmin(abs(frequencies - 10))], 900)
        self.assertLess(spectrum[np.argmin(abs(frequencies - 50))], 130)

    def test_auxiliary_review_channels_remain_time_aligned_in_encrypted_artifact_source(self) -> None:
        windows = np.zeros((1, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
        labels = ["EOG Left-Ref", "EOG Right-Ref", "ECG", "Chin 1-Chin 2", "Photic"]
        review = np.repeat(np.arange(5, dtype=np.float32)[:, None], 1024, axis=1)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "retained.npz"
            write_model_window_npz(
                artifact,
                windows,
                np.asarray([0.0]),
                np.asarray([0]),
                [(0.0, review)],
                labels,
            )
            preview = _read_npz_preview(artifact, [], 0.0, 4.0, 2048)
        self.assertEqual([item["label"] for item in preview["channels"][-5:]], labels)
        self.assertEqual(preview["channels"][-1]["time_seconds"], preview["time_seconds"])
        self.assertEqual(preview["channels"][-1]["samples"][0], 4.0)

    def test_model_window_npz_preserves_large_source_time_offsets(self) -> None:
        gap_seconds = float(2 * 365 * 24 * 60 * 60)
        starts = np.asarray([gap_seconds, gap_seconds + 2.0], dtype=np.float64)
        windows = np.zeros((2, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "retained.npz"
            write_model_window_npz(artifact, windows, starts, np.asarray([0, 1]))
            with np.load(artifact) as payload:
                saved_starts = payload["window_start_seconds"]
            preview = _read_npz_preview(artifact, [], gap_seconds, 6.0, 2048)

        self.assertEqual(saved_starts.dtype, np.float64)
        np.testing.assert_array_equal(saved_starts, starts)
        expected_times = gap_seconds + np.arange(6 * MODEL_SAMPLING_RATE, dtype=np.float64) / MODEL_SAMPLING_RATE
        np.testing.assert_array_equal(preview["time_seconds"], expected_times)

    def test_model_window_writer_rejects_offsets_without_sample_precision(self) -> None:
        windows = np.zeros((1, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
        starts = np.asarray([1e14], dtype=np.float64)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "retained.npz"
            with self.assertRaisesRegex(ValueError, "timestamp precision"):
                write_model_window_npz(artifact, windows, starts, np.asarray([0]))

    def test_npz_preview_rejects_legacy_offsets_without_sample_precision(self) -> None:
        windows = np.zeros((1, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "legacy-retained.npz"
            np.savez_compressed(
                artifact,
                model_windows=windows,
                window_start_seconds=np.asarray([1e14], dtype=np.float64),
            )
            with self.assertRaisesRegex(ValueError, "timestamp precision"):
                _read_npz_preview(artifact, [], 1e14, 4.0, 2048)

    def test_npz_preview_preserves_fractional_gap_times_and_segments(self) -> None:
        gap_start = 4.0000005
        starts = np.asarray([0.0, gap_start], dtype=np.float64)
        windows = np.zeros((2, 1024, len(MODEL_CHANNELS)), dtype=np.float32)
        windows[1] = 1.0
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "retained.npz"
            write_model_window_npz(artifact, windows, starts, np.asarray([0, 1]))
            preview = _read_npz_preview(artifact, [], 0.0, 8.01, 4096)

        times = np.asarray(preview["time_seconds"], dtype=np.float64)
        self.assertEqual(times[1024], gap_start)
        self.assertEqual(
            preview["segments"],
            [
                {"source_start_seconds": 0.0, "source_end_seconds": 4.0},
                {"source_start_seconds": gap_start, "source_end_seconds": gap_start + 4.0},
            ],
        )

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
                session = EEGSession(
                    session_id="SES-OVERLAP",
                    status=AnalysisStatus.COMPLETED,
                    privacy_method="metadata-scrub+signal-obfuscation",
                )
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

    def test_gapped_npz_preview_representation_matches_privacy_profile(self) -> None:
        profiles = (
            ("metadata-scrub", write_model_window_npz, "metadata-scrubbed"),
            (
                "metadata-scrub+signal-obfuscation",
                write_obfuscated_npz,
                "signal-obfuscated",
            ),
        )
        for index, (privacy_method, write_artifact, expected) in enumerate(profiles):
            with self.subTest(privacy_method=privacy_method), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                storage = SessionStorage(root / "sessions", b"s" * 32)
                source = root / "retained.npz"
                windows = np.random.default_rng(index).normal(
                    size=(1, 1024, len(MODEL_CHANNELS))
                ).astype(np.float32)
                write_artifact(source, windows, np.asarray([0.0]), np.asarray([0]))
                encrypted = storage.store_encrypted_artifact(
                    f"SES-REPRESENTATION-{index}",
                    source,
                    f"REC-REPRESENTATION-{index}.npz",
                )

                engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
                SQLModel.metadata.create_all(engine)
                with Session(engine) as db:
                    session = EEGSession(
                        session_id=f"SES-REPRESENTATION-{index}",
                        status=AnalysisStatus.COMPLETED,
                        privacy_method=privacy_method,
                    )
                    db.add(session)
                    db.commit()
                    db.refresh(session)
                    assert session.id is not None
                    record = EEGRecording(
                        record_id=f"REC-REPRESENTATION-{index}",
                        session_db_id=session.id,
                        sequence_index=1,
                        original_filename="",
                        duration_seconds=4,
                        status=RecordingStatus.INFERRED,
                        retained_artifact_path=str(encrypted),
                    )
                    db.add(record)
                    db.commit()
                    db.refresh(record)
                    assert record.id is not None
                    db.add(
                        Prediction(
                            recording_db_id=record.id,
                            window_index=0,
                            model_name="test-model",
                            model_version="1",
                            probability=0.9,
                            seizure_detected=True,
                            start_seconds=0,
                            end_seconds=4,
                        )
                    )
                    db.commit()
                    with patch("backend.app.services.signal_service.ENABLE_SIGNAL_PREVIEW", True):
                        preview = build_signal_preview(db, session, record, storage, 0, 4, 64)
                engine.dispose()
                self.assertEqual(preview["representation"], expected)

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
