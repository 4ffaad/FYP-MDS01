"""Worker-owned end-to-end EEG processing orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlmodel import Session, select

from backend.app.database.db import engine
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
from backend.app.eeg.model_input import preprocess_edf_to_npz
from backend.app.ml.model_loader import get_inference_service
from backend.app.privacy.deidentify import deidentify_edf, generate_record_id
from backend.app.services.explanation_service import write_stub_explanation
from backend.app.services.storage_service import SessionStorage
from backend.app.services.validation_service import ValidationError, validate_edf


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, (ValidationError, ValueError, RuntimeError)):
        return str(exc)[:500]
    return "Processing failed unexpectedly."


def _set_session_status(db: Session, session: EEGSession, status: AnalysisStatus, stage: str | None = None) -> None:
    session.status = status
    session.current_stage = stage
    db.add(session)
    db.commit()


def _begin_attempt(
    db: Session,
    session: EEGSession,
    job_id: str,
    stage: ProcessingStage,
    recording: EEGRecording | None = None,
) -> ProcessingAttempt:
    attempt = ProcessingAttempt(
        session_db_id=session.id,
        recording_db_id=recording.id if recording else None,
        job_id=job_id,
        stage=stage,
        status=ProcessingStatus.RUNNING,
        started_at=_now(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _finish_attempt(db: Session, attempt: ProcessingAttempt, status: ProcessingStatus, error: str | None = None) -> None:
    attempt.status = status
    attempt.error_message = error
    attempt.finished_at = _now()
    db.add(attempt)
    db.commit()


def process_session(session_id: str, job_id: str) -> None:
    storage = SessionStorage()
    with Session(engine) as db:
        session = db.exec(select(EEGSession).where(EEGSession.session_id == session_id)).first()
        if session is None or session.id is None:
            return

        try:
            inference = get_inference_service()
            _set_session_status(db, session, AnalysisStatus.VALIDATING, "validation")
            validation_attempt = _begin_attempt(db, session, job_id, ProcessingStage.VALIDATION)
            extracted_paths = storage.extract_edfs(session.session_id, Path(session.original_path))
            _finish_attempt(db, validation_attempt, ProcessingStatus.SUCCEEDED)
        except Exception as exc:
            error = _safe_error(exc)
            _finish_attempt(db, validation_attempt, ProcessingStatus.FAILED, error) if "validation_attempt" in locals() else None
            session.status = AnalysisStatus.FAILED
            session.current_stage = "validation"
            session.error_message = error
            session.completed_at = _now()
            db.add(session)
            db.commit()
            return

        records: list[EEGRecording] = []
        any_errors = False
        for sequence_index, extracted_path in enumerate(extracted_paths, start=1):
            record = EEGRecording(
                record_id=generate_record_id(),
                session_db_id=session.id,
                sequence_index=sequence_index,
                original_filename=extracted_path.name,
                extracted_path=str(extracted_path),
                status=RecordingStatus.VALIDATING,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            records.append(record)

            try:
                _process_record(db, session, record, storage, inference, job_id)
            except Exception as exc:
                any_errors = True
                record.status = RecordingStatus.FAILED
                record.error_message = _safe_error(exc)
                db.add(record)
                db.commit()

        session.status = AnalysisStatus.COMPLETED_WITH_ERRORS if any_errors else AnalysisStatus.COMPLETED
        session.current_stage = None
        session.completed_at = _now()
        db.add(session)
        db.commit()


def _process_record(db: Session, session: EEGSession, record: EEGRecording, storage: SessionStorage, inference, job_id: str) -> None:
    technical = validate_edf(Path(record.extracted_path or ""))
    record.duration_seconds = technical["duration_seconds"]
    record.sampling_rate = technical["sampling_rate"]
    record.channel_count = technical["channel_count"]
    db.add(record)
    db.commit()

    _set_session_status(db, session, AnalysisStatus.DEIDENTIFYING, "deidentification")
    deid_attempt = _begin_attempt(db, session, job_id, ProcessingStage.DEIDENTIFICATION, record)
    deid_path = storage.deidentified_path(session.session_id, record.record_id)
    try:
        deidentify_edf(record.extracted_path or "", deid_path, record.record_id)
        record.deidentified_path = str(deid_path)
        record.status = RecordingStatus.DEIDENTIFIED
        db.add(record)
        db.commit()
        _finish_attempt(db, deid_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, deid_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.PREPROCESSING, "preprocessing")
    prep_attempt = _begin_attempt(db, session, job_id, ProcessingStage.PREPROCESSING, record)
    processed_path = storage.processed_path(session.session_id, record.record_id)
    try:
        output_path, _details = preprocess_edf_to_npz(
            deid_path,
            record.record_id,
            output_path=processed_path,
        )
        record.preprocessed_path = str(output_path)
        record.status = RecordingStatus.PROCESSED
        db.add(record)
        db.commit()
        _finish_attempt(db, prep_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, prep_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.INFERENCE, "inference")
    inference_attempt = _begin_attempt(db, session, job_id, ProcessingStage.INFERENCE, record)
    try:
        with np.load(processed_path) as payload:
            windows = payload["model_windows"]
            starts = payload["window_start_seconds"]
        predictions = inference.predict(windows, starts, record.record_id)
        for prediction in predictions:
            db_prediction = Prediction(
                recording_db_id=record.id,
                window_index=prediction.window_index,
                model_name=inference.model_name,
                model_version=inference.model_version,
                probability=prediction.probability,
                seizure_detected=prediction.seizure_detected,
                start_seconds=prediction.start_seconds,
                end_seconds=prediction.end_seconds,
            )
            db.add(db_prediction)
        record.status = RecordingStatus.INFERRED
        db.add(record)
        db.commit()
        _finish_attempt(db, inference_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, inference_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.EXPLAINING, "explainability")
    explanation_attempt = _begin_attempt(db, session, job_id, ProcessingStage.EXPLAINABILITY, record)
    try:
        stored_predictions = list(
            db.exec(select(Prediction).where(Prediction.recording_db_id == record.id)).all()
        )
        for stored in stored_predictions:
            from backend.app.ml.interface import WindowPrediction

            explanation_path = storage.explanation_path(session.session_id, stored.id or 0)
            payload = write_stub_explanation(
                explanation_path,
                record_id=record.record_id,
                prediction=WindowPrediction(
                    window_index=stored.window_index,
                    start_seconds=stored.start_seconds,
                    end_seconds=stored.end_seconds,
                    probability=stored.probability,
                    seizure_detected=stored.seizure_detected,
                ),
            )
            db.add(
                Explanation(
                    prediction_db_id=stored.id,
                    method="development-stub",
                    explanation_path=str(explanation_path),
                    explanation_data=str(payload),
                    is_clinical=False,
                )
            )
        db.commit()
        _finish_attempt(db, explanation_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, explanation_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise
