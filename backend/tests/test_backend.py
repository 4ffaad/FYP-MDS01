"""Basic end-to-end checks using a small synthetic EDF fixture.

Run with: PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
"""

from datetime import datetime, timedelta, timezone
import asyncio
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
import zipfile
import warnings
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import numpy as np
import pyedflib
from fastapi import BackgroundTasks, UploadFile
from fastapi import HTTPException
from sqlalchemy import String
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
from backend.app.database.models.types import EnumString
from backend.app.database.repository import (
    get_recording_by_public_id,
    get_session_by_database_id,
    get_session_by_public_id,
    list_explanations,
    list_flagged_window_counts,
    list_predictions,
    list_recordings_for_session,
    list_sessions,
    get_upload_draft,
)
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.preprocessing import EEGPreprocessor
from backend.app.eeg.model_input import MODEL_CHANNELS, prepare_model_windows
from backend.app.ml.stub_inference import StubInferenceService
from backend.app.ml.interface import WindowPrediction, score_crossed_threshold
from backend.app.privacy.deidentify import deidentify_edf, generate_record_id, inspect_metadata, scrub_signal_header
from backend.app.privacy.signal_projection import obfuscate_signal, psd_features
from backend.app.privacy.methods import canonical_privacy_profile, methods_from_profile, normalize_privacy_methods
from backend.app.privacy.retention import detected_intervals, model_alert_intervals, select_window_indices, write_obfuscated_npz, write_scrubbed_edf_clip
from backend.app.research.metrics import calibration_metrics, classification_metrics, patient_bootstrap_f1, precision_recall_points, roc_points, threshold_sweep
from backend.app.research.chb_mit import (
    seizure_window_labels,
    sidecar_annotations,
    sidecar_path,
    summary_annotations,
)
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.session_service import cleanup_expired_drafts, create_session, create_upload_draft, delete_session, finalize_upload_draft, public_record, public_session
from backend.app.services.case_service import CaseReferenceError, ensure_case_reference, new_case_id
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
        physical_min: float = -1000,
        physical_max: float = 1000,
    ) -> np.ndarray:
        samples = np.asarray(
            [np.arange(sample_count, dtype=np.int32) - sample_count // 2 + index for index in range(len(labels))]
        )
        headers = [
            {
                "label": label,
                "dimension": "uV",
                "sample_frequency": 256,
                "physical_min": physical_min,
                "physical_max": physical_max,
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
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                deidentify_edf(source, output, anonymous_id)
            self.assertFalse(
                [warning for warning in captured if "Physical minimum" in str(warning.message) or "Physical maximum" in str(warning.message)]
            )

            self.assertTrue(output.exists())
            reader = pyedflib.EdfReader(str(output))
            try:
                copied = np.asarray([reader.readSignal(i, digital=True) for i in range(2)])
                self.assertTrue(np.array_equal(copied, original))
                self.assertEqual(reader.getSignalLabels(), ["FP1-F7", "F7-T7"])
                self.assertEqual(reader.getSampleFrequencies().tolist(), [256.0, 256.0])
                self.assertIn(reader.getPatientName(), {"", "X"})
                self.assertEqual(reader.getPatientCode(), "")
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

    def test_scrubbed_edf_is_warning_free_and_model_preprocessing_compatible(self) -> None:
        """Scrubbing keeps digital samples and the model tensor within tolerance."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "long-range.edf", root / "scrubbed.edf"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._create_source_edf(
                    source,
                    MODEL_CHANNELS,
                    sample_count=4096,
                    physical_min=-807.032967032967,
                    physical_max=1037.948717948718,
                )
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                deidentify_edf(source, output, generate_record_id())
            self.assertFalse(
                [
                    warning
                    for warning in captured
                    if "Physical minimum" in str(warning.message)
                    or "Physical maximum" in str(warning.message)
                ]
            )

            direct_windows, direct_starts, _ = prepare_model_windows(
                EEGPreprocessor(sampling_rate=256).preprocess(
                    read_uniform_edf(source)[0]
                ),
                256,
                list(MODEL_CHANNELS),
            )
            scrubbed_windows, scrubbed_starts, _ = prepare_model_windows(
                EEGPreprocessor(sampling_rate=256).preprocess(
                    read_uniform_edf(output)[0]
                ),
                256,
                list(MODEL_CHANNELS),
            )
            self.assertEqual(direct_windows.shape, (7, 1024, 18))
            self.assertEqual(direct_windows.dtype, np.float32)
            np.testing.assert_array_equal(direct_starts, scrubbed_starts)
            np.testing.assert_allclose(direct_windows, scrubbed_windows, rtol=1e-3, atol=1e-3)
            direct_predictions = StubInferenceService().predict(direct_windows, direct_starts, "REC-COMPAT")
            scrubbed_predictions = StubInferenceService().predict(scrubbed_windows, scrubbed_starts, "REC-COMPAT")
            self.assertEqual(direct_predictions, scrubbed_predictions)

    def test_scrubbing_expands_digital_bounds_without_clipping_samples(self) -> None:
        header = {
            "label": "FP1-F7",
            "digital_min": -2,
            "digital_max": 2,
            "physical_min": -1.0,
            "physical_max": 1.0,
            "transducer": "sensitive device",
            "prefilter": "private filter details",
        }
        samples = np.asarray([-7, -2, 0, 2, 9], dtype=np.int32)
        scrubbed = scrub_signal_header(header, digital_samples=samples)
        self.assertEqual((scrubbed["digital_min"], scrubbed["digital_max"]), (-7, 9))
        self.assertEqual(scrubbed["transducer"], "")
        self.assertEqual(scrubbed["prefilter"], "")

    def test_preprocessing_preserves_shape_and_clips_values(self) -> None:
        data = np.vstack((np.sin(np.linspace(0, 20, 512)), np.zeros(512)))
        processed = EEGPreprocessor(sampling_rate=256).preprocess(data)
        self.assertEqual(processed.shape, data.shape)
        self.assertLessEqual(np.abs(processed).max(), 5)

    def test_vectorized_preprocessing_matches_channelwise_contract(self) -> None:
        """The optimized multi-channel path must match the original filter order."""
        processor = EEGPreprocessor(sampling_rate=256)
        data = np.random.default_rng(7).normal(size=(3, 2048))
        expected_bandpass = np.vstack([processor.bandpass_filter(channel) for channel in data])
        expected_notch = np.vstack([processor.notch_filter(channel) for channel in expected_bandpass])
        expected_normalized = np.vstack([processor.normalize(channel) for channel in expected_notch])
        expected = processor.remove_artifacts(expected_normalized)

        actual = processor.preprocess(data)

        np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-6)
        self.assertEqual(actual.dtype, np.float64)

    def test_preprocessing_rejects_non_finite_samples(self) -> None:
        """NaN and infinity cannot reach either inference adapter."""
        data = np.zeros((2, 2048), dtype=np.float64)
        data[0, 10] = np.inf
        with self.assertRaisesRegex(ValueError, "non-finite"):
            EEGPreprocessor(sampling_rate=256).preprocess(data)

    def test_model_contract_constants_are_unchanged(self) -> None:
        """The reviewed model contract remains explicit in one place."""
        from backend.app.eeg.model_input import (
            MODEL_SAMPLING_RATE,
            WINDOW_SAMPLES,
            WINDOW_SECONDS,
            WINDOW_STEP_SAMPLES,
            WINDOW_STEP_SECONDS,
        )

        self.assertEqual(MODEL_SAMPLING_RATE, 256)
        self.assertEqual(WINDOW_SECONDS, 4)
        self.assertEqual(WINDOW_SAMPLES, 1024)
        self.assertEqual(WINDOW_STEP_SECONDS, 2)
        self.assertEqual(WINDOW_STEP_SAMPLES, 512)
        self.assertEqual(len(MODEL_CHANNELS), 18)
        self.assertEqual(MODEL_CHANNELS[:4], ("FP1-F7", "F7-T7", "T7-P7", "P7-O1"))
        self.assertEqual(MODEL_CHANNELS[-2:], ("FZ-CZ", "CZ-PZ"))

    def test_model_windows_match_the_trained_input_contract(self) -> None:
        labels = list(MODEL_CHANNELS)
        signals = np.arange(18 * 2048, dtype=np.float64).reshape(18, 2048)
        windows, starts, discarded = prepare_model_windows(signals, 256, labels)

        self.assertEqual(windows.shape, (3, 1024, 18))
        self.assertEqual(windows.dtype, np.float32)
        self.assertEqual(starts.tolist(), [0.0, 2.0, 4.0])
        self.assertEqual(discarded, 0)
        self.assertEqual(windows[0, 0, 0], signals[0, 0])
        self.assertEqual(windows[1, 0, 17], signals[17, 512])

    def test_model_windows_reject_ambiguous_channel_sets(self) -> None:
        """The model must not silently select duplicate or extra EDF channels."""
        duplicate_labels = list(MODEL_CHANNELS[:-1]) + [MODEL_CHANNELS[0], MODEL_CHANNELS[-1]]
        signals = np.zeros((len(duplicate_labels), 1024), dtype=np.float64)
        with self.assertRaisesRegex(ValueError, "duplicate|exactly the model's required channels"):
            prepare_model_windows(signals, 256, duplicate_labels)

        extra_labels = list(MODEL_CHANNELS) + ["EXTRA-CHANNEL"]
        signals = np.zeros((len(extra_labels), 1024), dtype=np.float64)
        with self.assertRaisesRegex(ValueError, "exactly the model's required channels"):
            prepare_model_windows(signals, 256, extra_labels)

    def test_model_windows_reject_non_finite_signal_values(self) -> None:
        """Invalid samples must not be converted into a model-compatible tensor."""
        signals = np.zeros((len(MODEL_CHANNELS), 1024), dtype=np.float64)
        signals[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            prepare_model_windows(signals, 256, list(MODEL_CHANNELS))

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
        transformed = obfuscate_signal(windows, b"t" * 32)
        projected = service.predict(transformed, starts, "REC-TEST")
        self.assertEqual(first, second)
        self.assertNotEqual(first, projected)
        self.assertEqual(service.model_name, "development-stub")
        self.assertEqual(service.model_version, "stub-0.1.0")
        self.assertTrue(all(0 <= item.probability <= 1 for item in first))
        self.assertTrue(all(item.seizure_detected == score_crossed_threshold(item.probability, service.threshold) for item in first))

    def test_stub_rejects_non_finite_or_wrong_dtype_input(self) -> None:
        """The development adapter enforces the same finite float32 contract."""
        service = StubInferenceService()
        starts = np.asarray([0.0], dtype=np.float32)
        non_finite = np.zeros((1, 1024, 18), dtype=np.float32)
        non_finite[0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            service.predict(non_finite, starts, "REC-NAN")
        with self.assertRaisesRegex(ValueError, "float32"):
            service.predict(np.zeros((1, 1024, 18), dtype=np.float64), starts, "REC-DTYPE")

    def test_alert_threshold_is_inclusive_for_stub_and_h5_scores(self) -> None:
        """Both inference adapters flag exactly scores at or above the configured boundary."""

        self.assertFalse(score_crossed_threshold(0.49, 0.5))
        self.assertTrue(score_crossed_threshold(0.50, 0.5))
        self.assertTrue(score_crossed_threshold(0.51, 0.5))

        from backend.app.ml.h5_inference import H5InferenceService

        service = H5InferenceService.__new__(H5InferenceService)
        service.model = MagicMock()
        service.model.predict.return_value = np.asarray([[0.49], [0.50], [0.51]], dtype=np.float32)
        service.threshold = 0.5
        service.score_type = "uncalibrated_probability"
        service.calibration_method = None
        service.temperature = None
        predictions = service.predict(
            np.zeros((3, 1024, 18), dtype=np.float32),
            np.asarray([0.0, 2.0, 4.0], dtype=np.float32),
            "REC-THRESHOLD",
        )
        self.assertEqual([item.seizure_detected for item in predictions], [False, True, True])
        self.assertTrue(all(item.seizure_detected == score_crossed_threshold(item.probability, service.threshold) for item in predictions))

    def test_h5_runtime_fails_closed_without_a_reviewed_contract(self) -> None:
        from backend.app.ml.h5_inference import H5InferenceService, H5ModelError

        with self.assertRaises(H5ModelError):
            H5InferenceService(Path("missing-model.h5"), Path("missing-contract.json"))

    def test_h5_runtime_requires_an_independent_contract_hash(self) -> None:
        from backend.app.ml import h5_inference
        from backend.app.ml.h5_inference import H5InferenceService, H5ModelError

        with tempfile.TemporaryDirectory() as directory:
            contract_path = Path(directory) / "model-contract.json"
            contract_path.write_text("{}", encoding="utf-8")
            with patch.object(h5_inference, "H5_CONTRACT_SHA256", ""):
                with patch.dict(sys.modules, {"tensorflow": types.ModuleType("tensorflow")}):
                    with self.assertRaisesRegex(H5ModelError, "independent hash"):
                        H5InferenceService(Path(directory) / "model.h5", contract_path)

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

    def test_upload_draft_encrypts_expires_and_finalizes_once(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            payload = b"PK\\x03\\x04private staged archive"
            with Session(engine) as db:
                draft = asyncio.run(
                    create_upload_draft(
                        db,
                        storage,
                        UploadFile(filename="recordings.zip", file=io.BytesIO(payload)),
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                    )
                )
                encrypted_path = Path(draft.encrypted_path)
                self.assertTrue(encrypted_path.exists())
                self.assertNotIn(payload, encrypted_path.read_bytes())
                self.assertIsNotNone(get_upload_draft(db, draft.draft_id))

                session = finalize_upload_draft(db, storage, draft.draft_id, "metadata-scrub")

                self.assertTrue(Path(session.original_path).exists())
                self.assertIsNone(get_upload_draft(db, draft.draft_id))
                self.assertFalse((storage.root / "_drafts" / draft.draft_id).exists())

            with Session(engine) as db:
                expiring = asyncio.run(
                    create_upload_draft(
                        db,
                        storage,
                        UploadFile(filename="expired.zip", file=io.BytesIO(payload)),
                        datetime.now(timezone.utc) - timedelta(minutes=1),
                    )
                )
                expiring_path = Path(expiring.encrypted_path)
                cleanup_expired_drafts(db, storage)
                self.assertIsNone(get_upload_draft(db, expiring.draft_id))
                self.assertFalse(expiring_path.exists())

    def test_pending_draft_quota_limits_repeated_staging(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
            with Session(engine) as db:
                drafts = [
                    asyncio.run(
                        create_upload_draft(
                            db,
                            storage,
                            UploadFile(filename=f"recordings-{index}.zip", file=io.BytesIO(b"small")),
                            expires_at,
                            owner_user_id=42,
                        )
                    )
                    for index in range(2)
                ]
                with self.assertRaisesRegex(StorageError, "Too many staged uploads"):
                    asyncio.run(
                        create_upload_draft(
                            db,
                            storage,
                            UploadFile(filename="recordings-3.zip", file=io.BytesIO(b"small")),
                            expires_at,
                            owner_user_id=42,
                        )
                    )
                for draft in drafts:
                    storage.delete_draft(draft.draft_id)
                    db.delete(draft)
                db.commit()

    def test_case_reference_is_owner_scoped_and_opaque(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        case_id = new_case_id()
        with Session(engine) as db:
            db.add(EEGSession(session_id="SES-CASE-OWNER", case_id=case_id, owner_user_id=7))
            db.commit()
            ensure_case_reference(db, case_id, 7)
            with self.assertRaises(CaseReferenceError):
                ensure_case_reference(db, case_id, 8)
            with self.assertRaises(CaseReferenceError):
                ensure_case_reference(db, "patient-name", 7)

    def test_signal_preview_returns_bounded_alert_intervals(self) -> None:
        from backend.app.services.signal_service import build_signal_preview

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            source = Path(directory) / "retained.npz"
            windows = np.zeros((2, 1024, 18), dtype=np.float32)
            starts = np.asarray([0.0, 4.0], dtype=np.float32)
            write_obfuscated_npz(source, windows, starts, np.asarray([0], dtype=np.int64))
            encrypted = storage.store_encrypted_artifact("SES-SIGNAL", source, "REC-SIGNAL.npz")
            with Session(engine) as db:
                session = EEGSession(session_id="SES-SIGNAL", status=AnalysisStatus.COMPLETED)
                db.add(session)
                db.commit()
                db.refresh(session)
                record = EEGRecording(
                    record_id="REC-SIGNAL",
                    session_db_id=session.id,
                    sequence_index=1,
                    original_filename="private.edf",
                    duration_seconds=20,
                    status=RecordingStatus.INFERRED,
                    retained_artifact_path=str(encrypted),
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                db.add(Prediction(
                    recording_db_id=record.id,
                    window_index=0,
                    model_name="development-stub",
                    model_version="stub-0.1.0",
                    probability=0.9,
                    seizure_detected=True,
                    start_seconds=0,
                    end_seconds=4,
                ))
                db.commit()

                with patch("backend.app.services.signal_service.ENABLE_SIGNAL_PREVIEW", True):
                    payload = build_signal_preview(db, session, record, storage, 0, 10, 100)

            self.assertEqual(payload["representation"], "signal-obfuscated")
            self.assertEqual(len(payload["channels"]), 18)
            self.assertEqual(payload["flagged_intervals"], [{"start_seconds": 0, "end_seconds": 4}])
            self.assertLessEqual(len(payload["time_seconds"]), 100)

    def test_signal_obfuscation_is_keyed_lossy_and_model_compatible(self) -> None:
        windows = np.random.default_rng(42).normal(size=(2, 1024, 18)).astype(np.float32)
        first = obfuscate_signal(windows, b"a" * 32)
        second = obfuscate_signal(windows, b"a" * 32)
        rotated = obfuscate_signal(windows, b"b" * 32)
        features = psd_features(first)
        self.assertEqual(features.shape, (2, 90))
        self.assertEqual(first.shape, (2, 1024, 18))
        self.assertEqual(first.dtype, np.float32)
        self.assertTrue(np.array_equal(first, second))
        self.assertFalse(np.array_equal(first, rotated))
        self.assertFalse(np.array_equal(first, windows))

    def test_privacy_profiles_are_ordered_and_canonical(self) -> None:
        self.assertEqual(normalize_privacy_methods(), ("metadata-scrub",))
        self.assertEqual(
            normalize_privacy_methods('["signal-obfuscation", "metadata-scrub"]'),
            ("metadata-scrub", "signal-obfuscation"),
        )
        self.assertEqual(
            canonical_privacy_profile(("metadata-scrub", "signal-obfuscation")),
            "metadata-scrub+signal-obfuscation",
        )
        self.assertEqual(
            normalize_privacy_methods(legacy_method="signal-obfuscation"),
            ("metadata-scrub", "signal-obfuscation"),
        )
        self.assertEqual(
            methods_from_profile("cancellable-signal-projection"),
            ("metadata-scrub", "signal-obfuscation"),
        )
        with self.assertRaises(ValueError):
            normalize_privacy_methods("cancellable-signal-projection")

    def test_model_alert_intervals_merge_adjacent_positive_windows(self) -> None:
        predictions = [
            WindowPrediction(2, 12, 16, 0.8, True),
            WindowPrediction(0, 4, 8, 0.9, True),
            WindowPrediction(1, 8, 12, 0.7, True),
            WindowPrediction(3, 40, 44, 0.6, False),
            WindowPrediction(4, 44, 48, 0.95, True),
        ]
        self.assertEqual(model_alert_intervals(predictions), [(4.0, 16.0), (44.0, 48.0)])

    def test_retention_uses_model_positive_windows_and_context_only(self) -> None:
        predictions = [
            WindowPrediction(0, 4, 8, 0.9, True),
            WindowPrediction(1, 8, 12, 0.1, False),
            WindowPrediction(2, 200, 204, 0.8, True),
        ]
        intervals = detected_intervals(predictions, 300, context_seconds=60)
        self.assertEqual(intervals, [(0.0, 8.0), (140.0, 204.0)])
        starts = np.asarray([0, 4, 8, 140, 200, 280], dtype=np.float32)
        self.assertEqual(select_window_indices(starts, intervals).tolist(), [0, 1, 3, 4])

    def test_default_retention_context_is_bounded_to_ten_minutes(self) -> None:
        from backend.app.core.config import SIGNAL_RETENTION_CONTEXT_SECONDS

        self.assertEqual(SIGNAL_RETENTION_CONTEXT_SECONDS, 600)
        prediction = WindowPrediction(0, 900, 904, 0.9, True)
        self.assertEqual(detected_intervals([prediction], 2000), [(300.0, 904.0)])

    def test_metadata_retained_clip_is_scrubbed_and_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.edf"
            scrubbed = Path(directory) / "scrubbed.edf"
            clip = Path(directory) / "clip.edf"
            self._create_source_edf(source, MODEL_CHANNELS)
            deidentify_edf(source, scrubbed, generate_record_id())
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                write_scrubbed_edf_clip(scrubbed, clip, [(0, 2)])
            self.assertFalse(
                [warning for warning in captured if "Physical minimum" in str(warning.message) or "Physical maximum" in str(warning.message)]
            )
            reader = pyedflib.EdfReader(str(clip))
            try:
                self.assertEqual(reader.getStartdatetime().year, 1970)
                self.assertEqual(reader.getPatientCode(), "")
                self.assertEqual(reader.getSignalLabels(), list(MODEL_CHANNELS))
                self.assertEqual(reader.readSignal(0, digital=True).size, 512)
                self.assertEqual(reader.readAnnotations()[2].tolist(), [""])
            finally:
                reader.close()

    def test_retained_artifact_is_encrypted_and_plaintext_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", self.storage_key)
            source = Path(directory) / "clip.npz"
            source.write_bytes(b"private EEG samples")
            retained = storage.store_encrypted_artifact("SES-RETAINED", source, "REC-1.npz")
            self.assertFalse(source.exists())
            self.assertNotIn(b"private EEG samples", retained.read_bytes())
            storage.cleanup_session("SES-RETAINED", keep_retained=True)
            self.assertTrue(retained.exists())
            storage.delete_retained_artifact(retained)
            self.assertFalse(retained.exists())

    def test_offline_metrics_report_detection_and_calibration_values(self) -> None:
        labels = [0, 0, 1, 1]
        scores = [0.1, 0.8, 0.6, 0.9]
        metrics = classification_metrics(labels, scores, threshold=0.5)
        self.assertEqual(metrics["confusion_matrix"], [[1, 1], [0, 2]])
        self.assertAlmostEqual(float(metrics["sensitivity"]), 1.0)
        self.assertEqual(len(roc_points(labels, scores)["fpr"]), 6)
        self.assertEqual(len(precision_recall_points(labels, scores)["precision"]), 5)
        self.assertIn("brier_score", calibration_metrics(labels, scores))
        self.assertEqual(len(threshold_sweep(labels, scores, [0.25, 0.5, 0.75])), 3)
        bootstrap = patient_bootstrap_f1(labels, scores, ["p1", "p1", "p2", "p2"], repeats=10)
        self.assertLessEqual(bootstrap["lower_95"], bootstrap["upper_95"])

    def test_openapi_contains_only_current_routes(self) -> None:
        schema = app.openapi()
        paths = set(schema["paths"])
        self.assertNotIn("/api/v1/deidentify", paths)
        self.assertNotIn("/api/v1/preprocess/{session_id}", paths)
        self.assertIn("/api/sessions/upload", paths)
        self.assertIn("/api/uploads/drafts", paths)
        self.assertIn("/api/uploads/drafts/{draft_id}/finalize", paths)
        self.assertIn("/api/recordings/{record_id}/prediction", paths)
        self.assertNotIn("patient_reference", str(schema))

    def test_status_and_stage_columns_use_compatibility_safe_varchar_processing(self) -> None:
        columns = (
            EEGSession.__table__.c.status,
            EEGRecording.__table__.c.status,
            ProcessingAttempt.__table__.c.stage,
            ProcessingAttempt.__table__.c.status,
        )
        for column in columns:
            self.assertIsInstance(column.type, EnumString)
            self.assertIsInstance(column.type.impl, String)

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

    def test_optional_sidecars_are_internal_and_malformed_sidecars_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "optional-metadata.zip"
            valid_sidecar = bytes.fromhex(
                "005817fc23232074696d65207265736f6c7574696f6e3a2032353600"
                "00ecffffffff010000ec0b0000b4008000ec0000002800840000"
            )
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("recording_01.edf", b"edf")
                archive.writestr("recording_01.edf.seizures", valid_sidecar)
                archive.writestr("recording_02.edf", b"edf")
                archive.writestr("recording_02.edf.seizures", b"\x01\x80")

            annotations = SessionStorage(Path(directory) / "sessions", self.storage_key).read_reference_annotations(archive_path)

        self.assertEqual(annotations["recording_01.edf"], ("chb-mit-sidecar", [(2996.0, 3036.0)]))
        self.assertNotIn("recording_02.edf", annotations)

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
            patch("backend.app.api.sessions.processing_capacity.reserve", return_value=True),
            patch("backend.app.api.sessions.processing_capacity.run_reserved") as process,
        ):
            payload = asyncio.run(upload_session(tasks, archive, "metadata-scrub"))

        self.assertEqual(payload, {"session_id": "SES-BACKGROUND", "status": "queued"})
        self.assertNotIn("job_id", payload)
        create.assert_awaited_once_with(
            ANY,
            ANY,
            archive,
            "metadata-scrub",
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
        self.assertNotIn("reference_annotation", payload)
        self.assertNotIn("Jane", str(payload))

    def test_direct_recording_response_includes_safe_session_context(self) -> None:
        from backend.app.api.recordings import get_recording

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-RECORD-CONTEXT",
                privacy_method="metadata-scrub",
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
        self.assertEqual(payload["privacy_method"], "metadata-scrub")
        self.assertIn("session_created_at", payload)
        self.assertEqual(payload["source_filename"], "recording_12.edf")
        self.assertNotIn("patient", str(payload).lower())

    def test_prediction_api_exposes_calibration_provenance_without_recording_probability(self) -> None:
        """Calibrated window output stays distinct from a recording probability."""

        from backend.app.api.recordings import get_prediction

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(
                session_id="SES-CALIBRATED",
                privacy_method="metadata-scrub+signal-obfuscation",
                status=AnalysisStatus.COMPLETED,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-CALIBRATED",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="",
                status=RecordingStatus.INFERRED,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            db.add(
                Prediction(
                    recording_db_id=record.id,
                    window_index=0,
                    model_name="reviewed-h5",
                    model_version="h5-1",
                    threshold=0.5,
                    probability=0.8,
                    raw_score=0.7,
                    calibrated_probability=0.8,
                    score_type="calibrated_probability",
                    calibration_method="temperature_scaling",
                    calibration_version="temperature-scaling-v1",
                    calibration_dataset="CHB-MIT",
                    privacy_method=session.privacy_method,
                    seizure_detected=True,
                    start_seconds=0,
                    end_seconds=4,
                )
            )
            db.commit()
            payload = get_prediction(record.record_id, db)

        self.assertEqual(payload["model"]["privacy_method"], "metadata-scrub+signal-obfuscation")
        self.assertEqual(payload["model"]["calibration_version"], "temperature-scaling-v1")
        self.assertFalse(payload["summary"]["recording_probability_available"])
        self.assertEqual(payload["predictions"][0]["calibrated_probability"], 0.8)

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
        self.assertEqual(payload["summary"], {"model_alert_recordings": 1})
        self.assertEqual(payload["privacy_method"], "metadata-scrub")
        self.assertEqual(payload["privacy_methods"], ["metadata-scrub"])
        self.assertNotIn("reference_annotation", str(payload))
        self.assertNotIn("dataset_seizure_recordings", str(payload))
        self.assertEqual(payload["recordings"][0]["model_alert_window_count"], 1)
        self.assertEqual(payload["recordings"][0]["alert_intervals"], [{"start_seconds": 0.0, "end_seconds": 4.0}])
        self.assertEqual(flagged_counts, {completed.id: 1})

    def test_model_alert_is_independent_of_dataset_sidecar_reference(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            session = EEGSession(session_id="SES-NO-SIDECAR", status=AnalysisStatus.COMPLETED)
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-NO-SIDECAR",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="private.edf",
                status=RecordingStatus.INFERRED,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            db.add(Prediction(
                recording_db_id=record.id,
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

        self.assertEqual(payload["summary"]["model_alert_recordings"], 1)
        self.assertTrue(payload["recordings"][0]["model_alert"])
        self.assertNotIn("reference_annotation", str(payload))
        self.assertNotIn("dataset_seizure_recordings", str(payload))
        self.assertNotIn("retained_artifact_path", str(payload))

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
                        privacy_method="metadata-scrub+signal-obfuscation",
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
                self.assertEqual(session.privacy_method, "metadata-scrub+signal-obfuscation")
                self.assertEqual(records[0].status, RecordingStatus.INFERRED)
                self.assertEqual(len(predictions), 1)
                self.assertEqual(len(explanations), 1)
                self.assertEqual(session.original_path, "")
                self.assertIsNone(records[0].extracted_path)
                self.assertIsNone(records[0].deidentified_path)
                self.assertIsNone(records[0].preprocessed_path)
                self.assertTrue((storage.root / "SES-FULL").exists())
                retained_path = records[0].retained_artifact_path
                if retained_path:
                    self.assertTrue(Path(retained_path).exists())
                    self.assertEqual(Path(retained_path).parent.name, "retained")

    def test_full_signal_preview_retains_complete_transformed_recording_only_when_enabled(self) -> None:
        from backend.app.services.processing_service import process_session
        from backend.app.services.signal_service import build_signal_preview

        class PositiveStub:
            model_name = "development-stub"
            model_version = "stub-0.1.0"
            threshold = 0.5
            score_type = "development_score"
            calibration_method = None

            def predict(self, windows, window_starts, record_id, privacy_method="metadata-scrub"):
                return [
                    WindowPrediction(index, float(start), float(start + 4), 0.9, True)
                    for index, start in enumerate(window_starts.tolist())
                ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "full-preview.edf"
            self._create_source_edf(source, MODEL_CHANNELS, 2048)
            archive = root / "session.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.write(source, source.name)

            database = create_engine("sqlite://", connect_args={"check_same_thread": False})
            self.addCleanup(database.dispose)
            SQLModel.metadata.create_all(database)
            storage = SessionStorage(root / "sessions", self.storage_key)
            encrypted_archive = self._store_archive(storage, "SES-FULL-PREVIEW", archive)
            with Session(database) as db:
                db.add(EEGSession(session_id="SES-FULL-PREVIEW", original_filename="session.zip", original_path=str(encrypted_archive)))
                db.commit()

            with (
                patch("backend.app.services.processing_service.engine", database),
                patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
                patch("backend.app.services.processing_service.get_inference_service", return_value=PositiveStub()),
                patch("backend.app.services.processing_service.ENABLE_FULL_SIGNAL_PREVIEW", True),
            ):
                process_session("SES-FULL-PREVIEW")

            with Session(database) as db:
                session = get_session_by_public_id(db, "SES-FULL-PREVIEW")
                records = list_recordings_for_session(db, session.id)
                self.assertEqual(len(records), 1)
                self.assertIsNotNone(records[0].retained_artifact_path)
                with patch("backend.app.services.signal_service.ENABLE_SIGNAL_PREVIEW", True), patch("backend.app.services.signal_service.ENABLE_FULL_SIGNAL_PREVIEW", True):
                    payload = build_signal_preview(db, session, records[0], storage, 0, 8, 400)

            self.assertEqual(len(payload["channels"]), 18)
            self.assertGreaterEqual(payload["time_seconds"][-1], 7.0)

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
