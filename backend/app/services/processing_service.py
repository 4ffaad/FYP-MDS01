"""End-to-end EEG processing orchestration for FastAPI background tasks."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from sqlmodel import Session

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
from backend.app.database.repository import (
    get_session_by_public_id,
    list_predictions,
    list_recordings_for_session,
)
from backend.app.core.config import SIGNAL_RETENTION_CONTEXT_SECONDS, TEMPLATE_KEY_ENV
from backend.app.eeg.model_input import preprocess_edf_to_npz
from backend.app.ml.interface import InferenceService, WindowPrediction
from backend.app.ml.model_loader import get_inference_service
from backend.app.privacy.crypto import read_base64_key
from backend.app.privacy.deidentify import deidentify_edf, generate_record_id
from backend.app.privacy.retention import (
    detected_intervals,
    select_window_indices,
    write_obfuscated_npz,
    write_scrubbed_edf_clip,
)
from backend.app.privacy.signal_projection import obfuscate_signal
from backend.app.services.explanation_service import build_stub_explanation
from backend.app.services.storage_service import SessionStorage
from backend.app.services.validation_service import ValidationError, validate_edf


def _now() -> datetime:
    """Return the current UTC time for processing audit timestamps."""

    return datetime.now(timezone.utc)


def _safe_error(exc: Exception) -> str:
    """Convert an exception into a bounded, non-sensitive status message.

    Parameters
    ----------
    exc : Exception
        Internal exception raised by a pipeline stage.

    Returns
    -------
    str
        Safe message suitable for a database status row and API response.
    """

    if isinstance(exc, (ValidationError, ValueError, RuntimeError)):
        return str(exc)[:500]
    return "Processing failed unexpectedly."


def _set_session_status(db: Session, session: EEGSession, status: AnalysisStatus, stage: str | None = None) -> None:
    """Persist the current session status and pipeline stage.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session owned by the background task.
    session : EEGSession
        Session row being processed.
    status : AnalysisStatus
        New session-level state.
    stage : str or None
        Human-readable current pipeline stage.
    """

    session.status = status
    session.current_stage = stage
    db.add(session)
    db.commit()


def _begin_attempt(
    db: Session,
    session: EEGSession,
    stage: ProcessingStage,
    recording: EEGRecording | None = None,
) -> ProcessingAttempt:
    """Create and persist a running processing-attempt audit row.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session owned by the background task.
    session : EEGSession
        Session being processed.
    stage : ProcessingStage
        Pipeline stage being started.
    recording : EEGRecording or None
        Recording row when the attempt is recording-specific.

    Returns
    -------
    ProcessingAttempt
        Persisted running attempt with its database ID.
    """

    attempt = ProcessingAttempt(
        session_db_id=session.id,
        recording_db_id=recording.id if recording else None,
        stage=stage,
        status=ProcessingStatus.RUNNING,
        started_at=_now(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _finish_attempt(db: Session, attempt: ProcessingAttempt, status: ProcessingStatus, error: str | None = None) -> None:
    """Complete one processing-attempt audit row.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session owned by the background task.
    attempt : ProcessingAttempt
        Attempt row to update.
    status : ProcessingStatus
        Final success or failure state.
    error : str or None
        Safe bounded error message, if the stage failed.
    """

    attempt.status = status
    attempt.error_message = error
    attempt.finished_at = _now()
    db.add(attempt)
    db.commit()


def _mark_session_failed(db: Session, session_id: str, error: str) -> None:
    """Rollback a failed transaction and persist a safe terminal status.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session whose failed transaction must be cleared first.
    session_id : str
        Opaque public session identifier to update.
    error : str
        Bounded, non-sensitive failure message.

    Returns
    -------
    None
        The session is marked failed when it still exists.
    """

    db.rollback()
    failed_session = get_session_by_public_id(db, session_id)
    if failed_session is None:
        return
    failed_session.status = AnalysisStatus.FAILED
    failed_session.current_stage = None
    failed_session.error_message = error[:500]
    failed_session.completed_at = _now()
    db.add(failed_session)
    db.commit()


def process_session(session_id: str) -> None:
    """Run validation and all per-recording stages for one queued session.

    Parameters
    ----------
    session_id : str
        Opaque session identifier created by the upload API.
    Returns
    -------
    None
        State, errors, predictions, and safe explanations are persisted
        in PostgreSQL. A malformed recording does not stop sibling recordings.

    Privacy
    -------
    Original and full derived waveform files are removed after processing.
    Only encrypted artifacts around model-positive windows are retained for
    private research review; safe result metadata remains available through
    the API.
    """

    storage = SessionStorage()
    with Session(engine) as db:
        session = get_session_by_public_id(db, session_id)
        if session is None or session.id is None:
            return

        try:
            validation_attempt: ProcessingAttempt | None = None
            try:
                inference = get_inference_service()
                _set_session_status(db, session, AnalysisStatus.VALIDATING, "validation")
                validation_attempt = _begin_attempt(db, session, ProcessingStage.VALIDATION)
                archive_path = storage.materialize_archive(session.session_id, Path(session.original_path))
                reference_annotations = storage.read_reference_annotations(archive_path)
                extracted_paths = storage.extract_edfs(session.session_id, archive_path)
                _finish_attempt(db, validation_attempt, ProcessingStatus.SUCCEEDED)
            except Exception as exc:
                error = _safe_error(exc)
                if validation_attempt is not None:
                    _finish_attempt(db, validation_attempt, ProcessingStatus.FAILED, error)
                session.status = AnalysisStatus.FAILED
                session.current_stage = "validation"
                session.error_message = error
                session.completed_at = _now()
                db.add(session)
                db.commit()
                return

            any_errors = False
            records: list[EEGRecording] = []
            for sequence_index, extracted_path in enumerate(extracted_paths, start=1):
                reference = reference_annotations.get(extracted_path.name.lower())
                record = EEGRecording(
                    record_id=generate_record_id(),
                    session_db_id=session.id,
                    sequence_index=sequence_index,
                    original_filename="",
                    extracted_path=str(extracted_path),
                    reference_annotation_source=reference[0] if reference else None,
                    reference_intervals_json=json.dumps(reference[1]) if reference else None,
                    status=RecordingStatus.VALIDATING,
                )
                db.add(record)
                records.append(record)
            db.commit()
            for record in records:
                db.refresh(record)

            for record in records:
                try:
                    _process_record(db, session, record, storage, inference)
                except Exception as exc:
                    any_errors = True
                    if record.retained_artifact_path:
                        storage.delete_retained_artifact(Path(record.retained_artifact_path))
                        record.retained_artifact_path = None
                    record.status = RecordingStatus.FAILED
                    record.error_message = _safe_error(exc)
                    db.add(record)
                    db.commit()

            session.status = AnalysisStatus.COMPLETED_WITH_ERRORS if any_errors else AnalysisStatus.COMPLETED
            session.current_stage = None
            session.completed_at = _now()
            db.add(session)
            db.commit()
        except Exception as exc:
            _mark_session_failed(db, session_id, _safe_error(exc))
        finally:
            # A failed flush leaves SQLAlchemy unusable until rollback. Clear
            # that state before touching private storage or querying records.
            db.rollback()
            storage.cleanup_session(session_id, keep_retained=True)
            db.rollback()
            current_session = get_session_by_public_id(db, session_id)
            if current_session is None or current_session.id is None:
                return
            current_session.original_path = ""
            for record in list_recordings_for_session(db, current_session.id):
                record.extracted_path = None
                record.preprocessed_path = None
                record.deidentified_path = None
                db.add(record)
            db.add(current_session)
            db.commit()


def _process_record(
    db: Session,
    session: EEGSession,
    record: EEGRecording,
    storage: SessionStorage,
    inference: InferenceService,
) -> None:
    """Process one extracted EDF through all remaining pipeline stages.

    Parameters
    ----------
    db : sqlmodel.Session
        Database session owned by the background task.
    session : EEGSession
        Parent session row.
    record : EEGRecording
        Recording row being processed.
    storage : SessionStorage
        Session-scoped private storage service.
    inference : InferenceService
        Configured real or development inference adapter.
    Returns
    -------
    None
        Updates the recording, prediction, explanation, and attempt tables.

    Raises
    ------
    Exception
        Stage errors are re-raised to the session coordinator, which marks
        only this recording as failed and continues with the next one.
    """

    technical = validate_edf(Path(record.extracted_path or ""))
    record.duration_seconds = technical["duration_seconds"]
    record.sampling_rate = technical["sampling_rate"]
    record.channel_count = technical["channel_count"]
    db.add(record)
    db.commit()

    _set_session_status(db, session, AnalysisStatus.DEIDENTIFYING, "deidentification")
    deid_attempt = _begin_attempt(db, session, ProcessingStage.DEIDENTIFICATION, record)
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
    prep_attempt = _begin_attempt(db, session, ProcessingStage.PREPROCESSING, record)
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
    inference_attempt = _begin_attempt(db, session, ProcessingStage.INFERENCE, record)
    try:
        with np.load(processed_path) as payload:
            windows = payload["model_windows"]
            starts = payload["window_start_seconds"]
        model_windows = windows
        if session.privacy_method == "signal-obfuscation":
            model_windows = obfuscate_signal(windows, read_base64_key(TEMPLATE_KEY_ENV))
        predictions = inference.predict(model_windows, starts, record.record_id)
        for prediction in predictions:
            db_prediction = Prediction(
                recording_db_id=record.id,
                window_index=prediction.window_index,
                model_name=inference.model_name,
                model_version=inference.model_version,
                threshold=inference.threshold,
                probability=prediction.probability,
                raw_score=prediction.raw_score,
                calibrated_probability=prediction.calibrated_probability,
                score_type=prediction.score_type,
                calibration_method=prediction.calibration_method,
                seizure_detected=prediction.seizure_detected,
                start_seconds=prediction.start_seconds,
                end_seconds=prediction.end_seconds,
            )
            db.add(db_prediction)
        db.add(record)
        db.commit()
        _finish_attempt(db, inference_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, inference_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.EXPLAINING, "explainability")
    explanation_attempt = _begin_attempt(db, session, ProcessingStage.EXPLAINABILITY, record)
    try:
        stored_predictions = list_predictions(db, record.id)
        for stored in stored_predictions:
            payload = build_stub_explanation(
                record_id=record.record_id,
                prediction=WindowPrediction(
                    window_index=stored.window_index,
                    start_seconds=stored.start_seconds,
                    end_seconds=stored.end_seconds,
                    probability=stored.probability,
                    seizure_detected=stored.seizure_detected,
                    score_type=stored.score_type,
                    calibration_method=stored.calibration_method,
                    raw_score=stored.raw_score,
                    calibrated_probability=stored.calibrated_probability,
                ),
            )
            db.add(
                Explanation(
                    prediction_db_id=stored.id,
                    method="development-stub",
                    explanation_path="",
                    explanation_data=json.dumps(payload),
                    is_clinical=False,
                )
            )
        db.commit()
        record.retained_artifact_path = _retain_positive_artifact(
            session=session,
            record=record,
            storage=storage,
            deidentified_path=deid_path,
            model_windows=model_windows,
            window_starts=starts,
            predictions=predictions,
        )
        record.status = RecordingStatus.INFERRED
        db.add(record)
        db.commit()
        _finish_attempt(db, explanation_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _finish_attempt(db, explanation_attempt, ProcessingStatus.FAILED, _safe_error(exc))
        raise


def _retain_positive_artifact(
    *,
    session: EEGSession,
    record: EEGRecording,
    storage: SessionStorage,
    deidentified_path: Path,
    model_windows: np.ndarray,
    window_starts: np.ndarray,
    predictions: list[WindowPrediction],
) -> str | None:
    """Encrypt only model-positive EEG segments for private retention.

    Parameters
    ----------
    session : EEGSession
        Session containing the selected privacy method.
    record : EEGRecording
        Recording whose model output was generated.
    storage : SessionStorage
        Private storage service for temporary and retained artifacts.
    deidentified_path : pathlib.Path
        Full metadata-scrubbed EDF used during processing.
    model_windows : numpy.ndarray
        Model input after the selected privacy transformation.
    window_starts : numpy.ndarray
        Start time of every model window.
    predictions : list[WindowPrediction]
        Model outputs used to determine retained ranges.

    Returns
    -------
    str or None
        Internal encrypted artifact path when a model alert exists.
    """

    intervals = detected_intervals(
        predictions,
        record.duration_seconds or 0.0,
        SIGNAL_RETENTION_CONTEXT_SECONDS,
    )
    if not intervals:
        return None

    temporary_dir = storage.directory(session.session_id, "work")
    if session.privacy_method == "metadata-scrub":
        temporary_path = temporary_dir / f"{record.record_id}.retained.edf"
        write_scrubbed_edf_clip(deidentified_path, temporary_path, intervals)
        return str(storage.store_encrypted_artifact(session.session_id, temporary_path, f"{record.record_id}.edf"))

    indexes = select_window_indices(window_starts, intervals)
    if not len(indexes):
        return None
    temporary_path = temporary_dir / f"{record.record_id}.retained.npz"
    write_obfuscated_npz(temporary_path, model_windows, window_starts, indexes)
    return str(storage.store_encrypted_artifact(session.session_id, temporary_path, f"{record.record_id}.npz"))
