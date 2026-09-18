"""Regression tests for recording-level processing cleanup."""

import asyncio
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from fastapi import UploadFile
from sqlmodel import Session, SQLModel, create_engine, select

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
    UploadDraft,
)
from backend.app.database.repository import get_session_by_public_id, get_upload_draft, list_predictions, list_predictions_for_processing, list_recordings_for_session
from backend.app.ml.interface import WindowPrediction
from backend.app.ml.h5_inference import H5InferenceService, H5ModelError
from backend.app.services.explanation_service import build_score_summary
from backend.app.services.processing_service import _process_record, process_session, sweep_interrupted_sessions
from backend.app.services.session_service import create_session, create_upload_draft, finalize_upload_draft
from backend.app.services.storage_service import SessionStorage, StorageError


class ProcessingFailureTests(unittest.TestCase):
    """Ensure a late stage failure cannot leave a public model alert behind."""

    def test_failed_recording_removes_predictions_and_explanations(self) -> None:
        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with Session(database) as db:
            db.add(
                EEGSession(
                    session_id="SES-LATE-FAILURE",
                    original_filename="",
                    original_path="/private/archive.enc",
                )
            )
            db.commit()

        storage = MagicMock()
        storage.materialize_archive.return_value = Path("/private/archive.zip")
        storage.read_reference_annotations.return_value = {}
        storage.extract_edfs.return_value = [Path("/private/recording.edf")]

        def fail_after_outputs(db, _session, record, _storage, inference):
            prediction = Prediction(
                recording_db_id=record.id,
                window_index=0,
                model_name="development-stub",
                model_version="stub-0.1.0",
                threshold=0.5,
                probability=0.9,
                raw_score=0.9,
                score_type="development_score",
                seizure_detected=True,
                start_seconds=0,
                end_seconds=4,
            )
            db.add(prediction)
            db.commit()
            db.refresh(prediction)
            db.add(
                Explanation(
                    prediction_db_id=prediction.id,
                    method="development-stub",
                    explanation_path="",
                    explanation_data="{}",
                )
            )
            record.retained_artifact_path = "/private/retained.enc"
            db.add(record)
            db.commit()
            raise RuntimeError("late stage failure")

        with (
            patch("backend.app.services.processing_service.engine", database),
            patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
            patch("backend.app.services.processing_service._process_record", side_effect=fail_after_outputs),
        ):
            process_session("SES-LATE-FAILURE")

        with Session(database) as db:
            session = get_session_by_public_id(db, "SES-LATE-FAILURE")
            self.assertEqual(session.status, AnalysisStatus.COMPLETED_WITH_ERRORS)
            record = list_recordings_for_session(db, session.id)[0]
            self.assertEqual(record.status, RecordingStatus.FAILED)
            self.assertIsNone(record.retained_artifact_path)
            self.assertEqual(db.exec(select(Prediction)).all(), [])
            self.assertEqual(db.exec(select(Explanation)).all(), [])
        storage.delete_retained_artifact.assert_called_once_with(Path("/private/retained.enc"))

    def test_record_cleanup_failure_keeps_terminal_failure_retryable(self) -> None:
        """A cleanup error cannot leave a failed recording publicly inferred."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with Session(database) as db:
            db.add(EEGSession(session_id="SES-RETRY-CLEANUP", original_path="/private/archive.enc"))
            db.commit()

        storage = MagicMock()
        storage.materialize_archive.return_value = Path("/private/archive.zip")
        storage.read_reference_annotations.return_value = {}
        storage.extract_edfs.return_value = [Path("/private/recording.edf")]
        storage.delete_retained_artifact.side_effect = StorageError("private cleanup failed")

        def fail_after_outputs(db, _session, record, _storage, _inference):
            db.add(Prediction(
                recording_db_id=record.id,
                window_index=0,
                model_name="test-model",
                model_version="1",
                probability=0.9,
                seizure_detected=True,
                start_seconds=0,
                end_seconds=4,
            ))
            record.status = RecordingStatus.INFERRED
            record.retained_artifact_path = "/private/retained.enc"
            db.add(record)
            db.commit()
            raise RuntimeError("private internal failure")

        with (
            patch("backend.app.services.processing_service.engine", database),
            patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
            patch("backend.app.services.processing_service._process_record", side_effect=fail_after_outputs),
        ):
            process_session("SES-RETRY-CLEANUP")

        with Session(database) as db:
            session = get_session_by_public_id(db, "SES-RETRY-CLEANUP")
            record = list_recordings_for_session(db, session.id)[0]
            self.assertEqual(session.status, AnalysisStatus.COMPLETED_WITH_ERRORS)
            self.assertEqual(record.status, RecordingStatus.FAILED)
            self.assertEqual(record.retained_artifact_path, "/private/retained.enc")
            self.assertEqual(db.exec(select(Prediction)).all(), [])
            self.assertNotIn("private internal failure", record.error_message or "")

    def test_predictions_are_private_until_recording_is_inferred(self) -> None:
        """An active recording must not publish partially committed model output."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with Session(database) as db:
            session = EEGSession(session_id="SES-ACTIVE")
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-ACTIVE",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="",
                status=RecordingStatus.PROCESSED,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            db.add(Prediction(
                recording_db_id=record.id,
                window_index=0,
                model_name="test-model",
                model_version="1",
                probability=0.9,
                seizure_detected=True,
                start_seconds=0,
                end_seconds=4,
            ))
            db.commit()

            self.assertEqual(list_predictions(db, record.id), [])
            self.assertEqual(len(list_predictions_for_processing(db, record.id)), 1)

    def test_retained_artifact_is_removed_when_record_commit_fails(self) -> None:
        """A commit failure after encryption cannot orphan a retained EEG clip."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            session = EEGSession(session_id="SES-ARTIFACT", privacy_method="metadata-scrub")
            db.add(session)
            db.commit()
            db.refresh(session)
            record = EEGRecording(
                record_id="REC-ARTIFACT",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="",
                extracted_path="/private/recording.edf",
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            class PositiveInference:
                model_name = "test-model"
                model_version = "1"
                threshold = 0.5
                score_type = "uncalibrated_probability"
                calibration_method = None

                def predict(self, windows, starts, _record_id, privacy_method="metadata-scrub"):
                    return [WindowPrediction(0, float(starts[0]), float(starts[0] + 4), 0.9, True, score_type=self.score_type, raw_score=0.9)]

            artifact = storage.directory(session.session_id, "retained") / "REC-ARTIFACT.edf.enc"

            def retain_artifact(**_kwargs):
                artifact.write_bytes(b"encrypted")
                return str(artifact)

            real_commit = db.commit
            failed_once = False

            def fail_artifact_commit():
                nonlocal failed_once
                if not failed_once and record.retained_artifact_path:
                    failed_once = True
                    raise RuntimeError("injected commit failure")
                real_commit()

            pipeline_calls: list[tuple[str, str]] = []

            def scrub_before_model(source_path, destination_path, _record_id):
                pipeline_calls.append(("scrub", str(destination_path)))
                return Path(destination_path)

            def preprocess_scrubbed(path):
                pipeline_calls.append(("preprocess", str(path)))
                return np.zeros((1, 1024, 18), dtype=np.float32), np.asarray([0.0], dtype=np.float32), {}

            with (
                patch("backend.app.services.processing_service.validate_edf", return_value={"duration_seconds": 4.0, "sampling_rate": 256, "channel_count": 18}),
                patch("backend.app.services.processing_service.deidentify_edf", side_effect=scrub_before_model),
                patch("backend.app.services.processing_service.preprocess_edf", side_effect=preprocess_scrubbed),
                patch("backend.app.services.processing_service._retain_positive_artifact", side_effect=retain_artifact),
                patch.object(db, "commit", side_effect=fail_artifact_commit),
            ):
                with self.assertRaisesRegex(RuntimeError, "injected commit failure"):
                    _process_record(db, session, record, storage, PositiveInference())

            self.assertEqual([call[0] for call in pipeline_calls], ["scrub", "preprocess"])
            self.assertEqual(pipeline_calls[0][1], pipeline_calls[1][1])

            self.assertFalse(artifact.exists())
            attempts = db.exec(select(ProcessingAttempt).where(ProcessingAttempt.stage == ProcessingStage.EXPLAINABILITY)).all()
            self.assertEqual(attempts[-1].status, ProcessingStatus.FAILED)
            self.assertIsNotNone(attempts[-1].finished_at)

    def test_upload_commit_failure_removes_archive_and_session_row(self) -> None:
        """A database failure after encrypted storage leaves no orphan session."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            archive = UploadFile(filename="recordings.zip", file=io.BytesIO(b"PK\x03\x04test"))
            with patch.object(db, "commit", side_effect=RuntimeError("injected commit failure")):
                with self.assertRaisesRegex(RuntimeError, "injected commit failure"):
                    asyncio.run(create_session(db, storage, archive))

            self.assertEqual(db.exec(select(EEGSession)).all(), [])
            self.assertEqual(list(storage.root.iterdir()), [])

    def test_cancelled_session_upload_removes_archive_and_session_row(self) -> None:
        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            archive = UploadFile(filename="recordings.zip", file=io.BytesIO(b"PK\x03\x04test"))
            with patch.object(storage, "save_upload", new=AsyncMock(side_effect=asyncio.CancelledError)):
                with self.assertRaises(asyncio.CancelledError):
                    asyncio.run(create_session(db, storage, archive))

            self.assertEqual(db.exec(select(EEGSession)).all(), [])
            if storage.root.exists():
                self.assertEqual(list(storage.root.iterdir()), [])
            self.assertTrue(archive.file.closed)

    def test_cancelled_draft_upload_removes_archive_and_draft_row(self) -> None:
        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            archive = UploadFile(filename="recordings.zip", file=io.BytesIO(b"PK\x03\x04test"))
            with patch.object(storage, "save_draft_upload", new=AsyncMock(side_effect=asyncio.CancelledError)):
                with self.assertRaises(asyncio.CancelledError):
                    asyncio.run(
                        create_upload_draft(
                            db,
                            storage,
                            archive,
                            datetime.now(timezone.utc) + timedelta(minutes=30),
                        )
                    )

            self.assertEqual(db.exec(select(UploadDraft)).all(), [])
            if storage.root.exists():
                self.assertEqual(list(storage.root.iterdir()), [])
            self.assertTrue(archive.file.closed)

    def test_failed_draft_promotion_keeps_retryable_encrypted_draft(self) -> None:
        """A failed finalization keeps the staged upload consistent for retry."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            draft = asyncio.run(create_upload_draft(
                db,
                storage,
                UploadFile(filename="recordings.zip", file=io.BytesIO(b"PK\x03\x04test")),
                datetime.now(timezone.utc) + timedelta(minutes=30),
            ))
            draft_path = Path(draft.encrypted_path)

            with patch.object(db, "commit", side_effect=RuntimeError("injected commit failure")):
                with self.assertRaisesRegex(RuntimeError, "injected commit failure"):
                    finalize_upload_draft(db, storage, draft.draft_id)

            db.expire_all()
            self.assertTrue(draft_path.exists())
            self.assertEqual(db.exec(select(EEGSession)).all(), [])
            self.assertIsNotNone(get_upload_draft(db, draft.draft_id))
            retry = finalize_upload_draft(db, storage, draft.draft_id)
            self.assertTrue(Path(retry.original_path).exists())
            self.assertFalse(draft_path.exists())

    def test_finalization_does_not_report_failure_after_session_commit(self) -> None:
        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory, Session(database) as db:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            draft = asyncio.run(
                create_upload_draft(
                    db,
                    storage,
                    UploadFile(filename="recordings.zip", file=io.BytesIO(b"PK\x03\x04test")),
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                )
            )
            with patch.object(storage, "delete_draft", side_effect=StorageError("temporary cleanup failure")):
                session = finalize_upload_draft(db, storage, draft.draft_id)

            self.assertIsNotNone(get_session_by_public_id(db, session.session_id))
            self.assertTrue(Path(session.original_path).exists())
            self.assertTrue(Path(draft.encrypted_path).exists())

    def test_h5_runtime_rejects_non_finite_scores(self) -> None:
        """NaN cannot silently become a negative H5 prediction."""

        service = H5InferenceService.__new__(H5InferenceService)
        service.model = MagicMock()
        service.model.predict.return_value = np.asarray([[np.nan]], dtype=np.float32)
        service.threshold = 0.5
        service.score_type = "uncalibrated_probability"
        service.calibration_method = None
        service.temperature = None
        with self.assertRaises(H5ModelError):
            service.predict(
                np.zeros((1, 1024, 18), dtype=np.float32),
                np.asarray([0.0], dtype=np.float32),
                "REC-NAN",
            )

    def test_real_model_score_summary_is_not_labelled_as_stub_output(self) -> None:
        """A reviewed runtime receives a neutral score summary, not a fake explanation."""

        payload = build_score_summary(
            record_id="REC-H5",
            prediction=WindowPrediction(
                0,
                0.0,
                4.0,
                0.8,
                True,
                score_type="uncalibrated_probability",
                raw_score=0.8,
            ),
            model_name="reviewed-h5",
            model_version="1",
        )
        self.assertEqual(payload["method"], "window-score-summary")
        self.assertNotIn("deterministic development", payload["note"].lower())

    def test_startup_sweep_reconciles_interrupted_session(self) -> None:
        """An interrupted EEG task becomes terminal and loses transient files."""

        database = create_engine("sqlite://", connect_args={"check_same_thread": False})
        self.addCleanup(database.dispose)
        SQLModel.metadata.create_all(database)
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", b"s" * 32)
            original = storage.directory("SES-INTERRUPTED", "original") / "archive.zip.enc"
            extracted = storage.directory("SES-INTERRUPTED", "extracted") / "record.edf"
            original.write_bytes(b"encrypted")
            extracted.write_bytes(b"transient")
            with Session(database) as db:
                session = EEGSession(
                    session_id="SES-INTERRUPTED",
                    original_filename="archive.zip",
                    original_path=str(original),
                    status=AnalysisStatus.INFERENCE,
                    current_stage="inference",
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                record = EEGRecording(
                    record_id="REC-INTERRUPTED",
                    session_db_id=session.id,
                    sequence_index=1,
                    original_filename="record.edf",
                    extracted_path=str(extracted),
                    status=RecordingStatus.PROCESSING,
                )
                attempt = ProcessingAttempt(
                    session_db_id=session.id,
                    recording_db_id=None,
                    stage=ProcessingStage.INFERENCE,
                    status=ProcessingStatus.RUNNING,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(record)
                db.add(attempt)
                db.commit()

            with (
                patch("backend.app.services.processing_service.engine", database),
                patch("backend.app.services.processing_service.SessionStorage", return_value=storage),
            ):
                sweep_interrupted_sessions()

            with Session(database) as db:
                session = get_session_by_public_id(db, "SES-INTERRUPTED")
                record = list_recordings_for_session(db, session.id)[0]
                attempt = db.exec(select(ProcessingAttempt)).one()
                self.assertEqual(session.status, AnalysisStatus.FAILED)
                self.assertIsNone(session.current_stage)
                self.assertEqual(record.status, RecordingStatus.FAILED)
                self.assertIsNone(record.extracted_path)
                self.assertEqual(attempt.status, ProcessingStatus.FAILED)
                self.assertFalse(storage.root.joinpath("SES-INTERRUPTED").exists())


if __name__ == "__main__":
    unittest.main()
