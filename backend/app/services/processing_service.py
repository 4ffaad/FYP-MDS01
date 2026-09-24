"""End-to-end EEG processing orchestration for FastAPI background tasks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
from sqlalchemy import delete, inspect
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
from backend.app.database.repository import (
    get_session_by_public_id,
    list_predictions_for_processing,
    list_recordings_for_session,
)
from backend.app.core.config import (
    ENABLE_FULL_SIGNAL_PREVIEW,
    ENABLE_SHAP_EXPLANATIONS,
    CLEANUP_INTERVAL_SECONDS,
    SHAP_METADATA_BACKGROUND_PATH,
    SHAP_OBFUSCATED_BACKGROUND_PATH,
    SHAP_MAX_WINDOWS,
    SHAP_TIME_BINS,
    SIGNAL_RETENTION_CONTEXT_SECONDS,
    TEMPLATE_KEY_ENV,
)
from backend.app.eeg.model_input import preprocess_edf, preprocess_eeg
from backend.app.ml.interface import InferenceService, WindowPrediction
from backend.app.ml.model_loader import get_inference_service
from backend.app.ml.shap_explanation import ShapExplanationError, build_shap_explanations
from backend.app.privacy.crypto import read_base64_key
from backend.app.privacy.deidentify import deidentify_edf, deidentify_eeg, generate_record_id
from backend.app.privacy.methods import SIGNAL_OBFUSCATION, methods_from_profile
from backend.app.privacy.retention import (
    detected_intervals,
    select_window_indices,
    write_obfuscated_npz,
    write_scrubbed_edf_clip,
)
from backend.app.privacy.signal_projection import obfuscate_signal
from backend.app.services.explanation_service import build_score_summary
from backend.app.services.storage_service import SessionStorage
from backend.app.services.validation_service import ValidationError, validate_edf, validate_eeg


LOGGER = logging.getLogger(__name__)

_ACTIVE_SESSION_STATUSES = {
    AnalysisStatus.QUEUED,
    AnalysisStatus.VALIDATING,
    AnalysisStatus.DEIDENTIFYING,
    AnalysisStatus.PREPROCESSING,
    AnalysisStatus.INFERENCE,
    AnalysisStatus.EXPLAINING,
}
_INTERRUPTED_ERROR = "EEG processing was interrupted before completion."
_CLEANUP_ERROR = "Private EEG cleanup is pending and will be retried."


def _sha256_file(path: Path) -> str:
    """Hash a private source, including the Nicolet header that interprets it."""

    if path.is_symlink() or not path.is_file():
        raise ValidationError("EEG source file is not a regular private file.")
    digest = hashlib.sha256()
    if path.suffix.lower() == ".data":
        sources = ((b"data", path), (b"head", path.with_suffix(".head")))
        digest.update(b"MDS01-NICOLET-DATA-HEAD-v1\0")
        for role, source in sources:
            if source.is_symlink() or not source.is_file():
                raise ValidationError("Nicolet source pair is incomplete or unsafe.")
            digest.update(role + b"\0")
            digest.update(source.stat().st_size.to_bytes(8, "big"))
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
    else:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


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

    if isinstance(exc, ValidationError):
        return str(exc)[:500]
    if isinstance(exc, ValueError):
        return "The EEG input or processing request was invalid."
    if isinstance(exc, RuntimeError):
        return "The EEG processing runtime failed."
    return "Processing failed unexpectedly."


def _record_has_private_paths(record: EEGRecording) -> bool:
    """Return whether a recording still references private storage."""

    return any(
        getattr(record, name)
        for name in (
            "extracted_path",
            "deidentified_path",
            "preprocessed_path",
            "retained_artifact_path",
        )
    )


def sweep_interrupted_sessions() -> None:
    """Reconcile interrupted EEG work and retry incomplete private cleanup.

    Active sessions cannot survive a process restart because their work runs in
    an in-process background task. They are converted to a safe terminal
    failure, while any cleanup failure leaves internal paths populated so the
    next sweep can retry it. Paths are never serialized by this function.
    """

    schema = inspect(engine)
    if not schema.has_table(str(EEGSession.__tablename__)):
        return
    columns = {column["name"] for column in schema.get_columns(str(EEGSession.__tablename__))}
    if "owner_user_id" not in columns:
        return
    storage = SessionStorage()
    with Session(engine) as db:
        sessions = db.exec(select(EEGSession)).all()
        for session in sessions:
            if session.id is None:
                continue
            records = list_recordings_for_session(db, session.id)
            active = session.status in _ACTIVE_SESSION_STATUSES
            has_paths = bool(session.original_path) or any(
                _record_has_private_paths(record) for record in records
            )
            if not active and not has_paths:
                continue

            if active:
                session.status = AnalysisStatus.FAILED
                session.current_stage = None
                session.error_message = _INTERRUPTED_ERROR
                session.completed_at = _now()
                for record in records:
                    if record.id is not None:
                        _remove_record_outputs(db, record.id)
                    record.status = RecordingStatus.FAILED
                    record.error_message = _INTERRUPTED_ERROR
                    db.add(record)
                for attempt in db.exec(
                    select(ProcessingAttempt).where(
                        ProcessingAttempt.session_db_id == session.id,
                        ProcessingAttempt.status == ProcessingStatus.RUNNING,
                    )
                ).all():
                    attempt.status = ProcessingStatus.FAILED
                    attempt.error_message = _INTERRUPTED_ERROR
                    attempt.finished_at = _now()
                    db.add(attempt)

            keep_retained = (
                not active
                and session.status
                in {AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED_WITH_ERRORS}
            )
            cleanup_succeeded = True
            try:
                storage.cleanup_session(session.session_id, keep_retained=keep_retained)
            except Exception:
                cleanup_succeeded = False
                LOGGER.warning("EEG private cleanup unavailable; retrying later.")

            for record in records:
                if record.retained_artifact_path and (
                    not keep_retained or record.status == RecordingStatus.FAILED
                ):
                    try:
                        storage.delete_retained_artifact(Path(record.retained_artifact_path))
                    except Exception:
                        cleanup_succeeded = False
                    else:
                        record.retained_artifact_path = None
                if cleanup_succeeded:
                    record.extracted_path = None
                    record.deidentified_path = None
                    record.preprocessed_path = None
                db.add(record)
            if cleanup_succeeded:
                session.original_path = ""
            elif not active:
                session.current_stage = "cleanup"
                session.error_message = _CLEANUP_ERROR
            db.add(session)
            try:
                db.commit()
            except Exception:
                db.rollback()
                LOGGER.warning("EEG cleanup state could not be persisted; retrying later.")


async def eeg_retention_loop() -> None:
    """Retry interrupted EEG cleanup independently of API requests."""

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(sweep_interrupted_sessions)
        except Exception:
            LOGGER.warning("EEG retention cleanup unavailable; retrying.")


def _shap_background_for_profile(privacy_profile: str) -> Path:
    """Return the SHAP background matching the final model-input profile."""

    return (
        SHAP_OBFUSCATED_BACKGROUND_PATH
        if SIGNAL_OBFUSCATION in methods_from_profile(privacy_profile)
        else SHAP_METADATA_BACKGROUND_PATH
    )


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


def _fail_attempt(db: Session, attempt: ProcessingAttempt, error: str) -> None:
    """Rollback a broken stage transaction and persist its safe failure state."""

    attempt_id = attempt.id
    db.rollback()
    if attempt_id is None:
        return
    persisted_attempt = db.get(ProcessingAttempt, attempt_id)
    if persisted_attempt is None:
        return
    _finish_attempt(db, persisted_attempt, ProcessingStatus.FAILED, error)


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


def _remove_record_outputs(db: Session, recording_db_id: int) -> None:
    """Remove predictions and explanations produced by a failed recording."""

    prediction_ids = select(Prediction.id).where(
        Prediction.recording_db_id == recording_db_id
    )
    db.exec(
        delete(Explanation).where(Explanation.prediction_db_id.in_(prediction_ids))
    )
    db.exec(delete(Prediction).where(Prediction.recording_db_id == recording_db_id))


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
                candidate_events = storage.read_embedded_eeg_events(extracted_paths)
                embedded_events = candidate_events if isinstance(candidate_events, dict) else {}
                _finish_attempt(db, validation_attempt, ProcessingStatus.SUCCEEDED)
            except Exception as exc:
                error = _safe_error(exc)
                if validation_attempt is not None:
                    _fail_attempt(db, validation_attempt, error)
                _mark_session_failed(db, session_id, error)
                return

            any_errors = False
            records: list[EEGRecording] = []
            for sequence_index, extracted_path in enumerate(extracted_paths, start=1):
                reference = reference_annotations.get(extracted_path.name.lower())
                events = embedded_events.get(extracted_path.name.lower(), [])
                record = EEGRecording(
                    record_id=generate_record_id(),
                    session_db_id=session.id,
                    sequence_index=sequence_index,
                    original_filename="",
                    extracted_path=str(extracted_path),
                    reference_annotation_source=(
                        reference[0] if reference else "nicolet-embedded-events" if events else None
                    ),
                    reference_intervals_json=json.dumps(reference[1]) if reference else None,
                    annotation_events_json=json.dumps(events) if events else None,
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
                    record_db_id = record.id
                    db.rollback()
                    failed_record = db.get(EEGRecording, record_db_id) if record_db_id else None
                    if failed_record is None:
                        continue
                    retained_cleanup_failed = False
                    if failed_record.retained_artifact_path:
                        try:
                            storage.delete_retained_artifact(Path(failed_record.retained_artifact_path))
                        except Exception:
                            retained_cleanup_failed = True
                            LOGGER.warning("Failed EEG artifact cleanup will be retried.")
                    _remove_record_outputs(db, record_db_id)
                    if not retained_cleanup_failed:
                        failed_record.retained_artifact_path = None
                    failed_record.status = RecordingStatus.FAILED
                    failed_record.error_message = _safe_error(exc)
                    db.add(failed_record)
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
            cleanup_succeeded = True
            try:
                storage.cleanup_session(session_id, keep_retained=True)
            except Exception:
                cleanup_succeeded = False
                LOGGER.warning("EEG private cleanup unavailable; retrying later.")
            db.rollback()
            current_session = get_session_by_public_id(db, session_id)
            if current_session is None or current_session.id is None:
                return
            if cleanup_succeeded:
                current_session.original_path = ""
                for record in list_recordings_for_session(db, current_session.id):
                    record.extracted_path = None
                    record.preprocessed_path = None
                    record.deidentified_path = None
                    db.add(record)
            else:
                current_session.current_stage = "cleanup"
                current_session.error_message = _CLEANUP_ERROR
            db.add(current_session)
            try:
                db.commit()
            except Exception:
                db.rollback()
                LOGGER.warning("EEG cleanup state could not be persisted; retrying later.")


def _process_record(
    db: Session,
    session: EEGSession,
    record: EEGRecording,
    storage: SessionStorage,
    inference: InferenceService,
) -> None:
    """Process one extracted EEG recording through all remaining pipeline stages.

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

    extracted_path = Path(record.extracted_path or "")
    technical = validate_edf(extracted_path) if extracted_path.suffix.lower() == ".edf" else validate_eeg(extracted_path)
    record.duration_seconds = technical["duration_seconds"]
    record.sampling_rate = technical["sampling_rate"]
    record.channel_count = technical["channel_count"]
    record.source_format = technical.get(
        "format",
        "edf" if extracted_path.suffix.lower() == ".edf" else "nicolet",
    )
    record.source_checksum_sha256 = _sha256_file(extracted_path)
    conversion_details = technical.get("conversion_details")
    record.conversion_details_json = (
        json.dumps(conversion_details, sort_keys=True, separators=(",", ":"))
        if isinstance(conversion_details, dict)
        else None
    )
    db.add(record)
    db.commit()

    _set_session_status(db, session, AnalysisStatus.DEIDENTIFYING, "deidentification")
    deid_attempt = _begin_attempt(db, session, ProcessingStage.DEIDENTIFICATION, record)
    deid_path = storage.directory(session.session_id, "deidentified") / f"{record.record_id}.edf"
    try:
        if extracted_path.suffix.lower() == ".edf":
            deidentify_edf(record.extracted_path or "", deid_path, record.record_id)
        else:
            deidentify_eeg(record.extracted_path or "", deid_path, record.record_id)
        record.deidentified_path = str(deid_path)
        record.status = RecordingStatus.DEIDENTIFIED
        db.add(record)
        db.commit()
        _finish_attempt(db, deid_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _fail_attempt(db, deid_attempt, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.PREPROCESSING, "preprocessing")
    prep_attempt = _begin_attempt(db, session, ProcessingStage.PREPROCESSING, record)
    try:
        if extracted_path.suffix.lower() == ".edf":
            windows, starts, _details = preprocess_edf(str(deid_path))
        else:
            windows, starts, _details = preprocess_eeg(str(deid_path))
        record.preprocessed_path = None
        record.status = RecordingStatus.PROCESSED
        db.add(record)
        db.commit()
        _finish_attempt(db, prep_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _fail_attempt(db, prep_attempt, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.INFERENCE, "inference")
    inference_attempt = _begin_attempt(db, session, ProcessingStage.INFERENCE, record)
    try:
        model_windows = windows
        if SIGNAL_OBFUSCATION in methods_from_profile(session.privacy_method):
            model_windows = obfuscate_signal(windows, read_base64_key(TEMPLATE_KEY_ENV))
        predictions = inference.predict(
            model_windows,
            starts,
            record.record_id,
            privacy_method=session.privacy_method,
        )
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
                calibration_version=prediction.calibration_version,
                calibration_dataset=prediction.calibration_dataset,
                privacy_method=session.privacy_method,
                seizure_detected=prediction.seizure_detected,
                start_seconds=prediction.start_seconds,
                end_seconds=prediction.end_seconds,
            )
            db.add(db_prediction)
        db.add(record)
        db.commit()
        _finish_attempt(db, inference_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        _fail_attempt(db, inference_attempt, _safe_error(exc))
        raise

    _set_session_status(db, session, AnalysisStatus.EXPLAINING, "explainability")
    explanation_attempt = _begin_attempt(db, session, ProcessingStage.EXPLAINABILITY, record)
    retained_artifact_path: str | None = None
    try:
        stored_predictions = list_predictions_for_processing(db, record.id)
        shap_by_window: dict[int, dict] = {}
        if ENABLE_SHAP_EXPLANATIONS and hasattr(inference, "model"):
            try:
                shap_by_window = build_shap_explanations(
                    model=inference.model,
                    windows=model_windows,
                    predictions=predictions,
                    background_path=_shap_background_for_profile(session.privacy_method),
                    threshold=inference.threshold,
                    max_windows=SHAP_MAX_WINDOWS,
                    time_bins=SHAP_TIME_BINS,
                )
            except ShapExplanationError:
                # Attribution is optional research output. A failed explainer
                # must never discard valid model predictions or retained clips.
                shap_by_window = {}
        for stored in stored_predictions:
            payload = build_score_summary(
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
                    calibration_version=stored.calibration_version,
                    calibration_dataset=stored.calibration_dataset,
                ),
                model_name=stored.model_name,
                model_version=stored.model_version,
                threshold=stored.threshold,
                calibration_version=stored.calibration_version,
                calibration_dataset=stored.calibration_dataset,
                privacy_method=session.privacy_method,
            )
            attribution = shap_by_window.get(stored.window_index)
            if attribution is not None:
                payload["method"] = "shap-gradient"
                payload["research_attribution"] = attribution
            db.add(
                Explanation(
                    prediction_db_id=stored.id,
                    method=payload["method"],
                    explanation_path="",
                    explanation_data=json.dumps(payload),
                    is_clinical=False,
                )
            )
        db.commit()
        retained_artifact_path = _retain_positive_artifact(
            session=session,
            record=record,
            storage=storage,
            source_path=deid_path,
            model_windows=model_windows,
            window_starts=starts,
            predictions=predictions,
        )
        record.retained_artifact_path = retained_artifact_path
        record.status = RecordingStatus.INFERRED
        db.add(record)
        db.commit()
        _finish_attempt(db, explanation_attempt, ProcessingStatus.SUCCEEDED)
    except Exception as exc:
        db.rollback()
        if retained_artifact_path:
            try:
                storage.delete_retained_artifact(Path(retained_artifact_path))
            except Exception:
                LOGGER.warning("Failed EEG artifact cleanup will be retried.")
        _fail_attempt(db, explanation_attempt, _safe_error(exc))
        raise


def _retain_positive_artifact(
    *,
    session: EEGSession,
    record: EEGRecording,
    storage: SessionStorage,
    source_path: Path,
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
    source_path : pathlib.Path
        Private extracted EDF used only to create a scrubbed positive clip.
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

    alert_intervals = detected_intervals(
        predictions,
        record.duration_seconds or 0.0,
        SIGNAL_RETENTION_CONTEXT_SECONDS,
    )
    if not alert_intervals:
        return None
    intervals = [(0.0, record.duration_seconds or 0.0)] if ENABLE_FULL_SIGNAL_PREVIEW else alert_intervals

    temporary_dir = storage.directory(session.session_id, "work")
    if SIGNAL_OBFUSCATION not in methods_from_profile(session.privacy_method):
        temporary_path = temporary_dir / f"{record.record_id}.retained.edf"
        write_scrubbed_edf_clip(source_path, temporary_path, intervals)
        return str(storage.store_encrypted_artifact(session.session_id, temporary_path, f"{record.record_id}.edf"))

    indexes = np.arange(len(window_starts), dtype=np.int64) if ENABLE_FULL_SIGNAL_PREVIEW else select_window_indices(window_starts, intervals)
    if not len(indexes):
        return None
    temporary_path = temporary_dir / f"{record.record_id}.retained.npz"
    write_obfuscated_npz(temporary_path, model_windows, window_starts, indexes)
    return str(storage.store_encrypted_artifact(session.session_id, temporary_path, f"{record.record_id}.npz"))
