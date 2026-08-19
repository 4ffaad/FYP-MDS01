"""Persistent metadata for the EEG processing pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp.

    Returns
    -------
    datetime
        Current UTC time for database audit fields.
    """

    return datetime.now(timezone.utc)


class AnalysisStatus(str, Enum):
    """Session-level states for the asynchronous EEG pipeline."""

    QUEUED = "queued"
    VALIDATING = "validating"
    DEIDENTIFYING = "deidentifying"
    PREPROCESSING = "preprocessing"
    INFERENCE = "inference"
    EXPLAINING = "explaining"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class RecordingStatus(str, Enum):
    """Per-recording states within a session."""

    UPLOADED = "uploaded"
    VALIDATING = "validating"
    DEIDENTIFIED = "deidentified"
    PROCESSING = "processing"
    PROCESSED = "processed"
    INFERRED = "inferred"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    """Pipeline stages recorded in processing-attempt audit rows."""

    VALIDATION = "validation"
    DEIDENTIFICATION = "deidentification"
    PREPROCESSING = "preprocessing"
    INFERENCE = "inference"
    EXPLAINABILITY = "explainability"


class ProcessingStatus(str, Enum):
    """Execution states for an individual processing attempt."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EEGSession(SQLModel, table=True):
    """Database metadata for one uploaded EEG archive."""

    __tablename__ = "sessions"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    patient_reference: str = Field(index=True)
    privacy_method: str = Field(default="raw-control", max_length=64)
    original_filename: str = ""
    original_path: str = ""
    status: AnalysisStatus = Field(default=AnalysisStatus.QUEUED, index=True)
    current_stage: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class EEGRecording(SQLModel, table=True):
    """Database metadata for one EDF file extracted from a session archive."""

    __tablename__ = "recordings"

    id: int | None = Field(default=None, primary_key=True)
    record_id: str = Field(index=True, unique=True)
    session_db_id: int = Field(foreign_key="sessions.id", index=True)
    sequence_index: int = Field(default=1, ge=1)
    original_filename: str
    extracted_path: str | None = None
    deidentified_path: str | None = None
    preprocessed_path: str | None = None
    duration_seconds: float | None = None
    sampling_rate: int | None = None
    channel_count: int | None = None
    status: RecordingStatus = Field(default=RecordingStatus.UPLOADED, index=True)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ProcessingAttempt(SQLModel, table=True):
    """Audit row describing one background-task attempt at one stage."""

    __tablename__ = "processing_attempts"

    id: int | None = Field(default=None, primary_key=True)
    recording_db_id: int | None = Field(default=None, foreign_key="recordings.id", index=True)
    session_db_id: int = Field(foreign_key="sessions.id", index=True)
    stage: ProcessingStage
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Prediction(SQLModel, table=True):
    """Window-level output produced by a versioned inference service."""

    __tablename__ = "predictions"

    id: int | None = Field(default=None, primary_key=True)
    recording_db_id: int = Field(foreign_key="recordings.id", index=True)
    window_index: int = Field(ge=0)
    model_name: str
    model_version: str
    probability: float = Field(ge=0, le=1)
    seizure_detected: bool
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    created_at: datetime = Field(default_factory=utc_now)


class Explanation(SQLModel, table=True):
    """Metadata pointing to an explanation artifact for one prediction."""

    __tablename__ = "explanations"

    id: int | None = Field(default=None, primary_key=True)
    prediction_db_id: int = Field(foreign_key="predictions.id", index=True)
    method: str
    explanation_path: str
    explanation_data: str | None = None
    is_clinical: bool = False
    created_at: datetime = Field(default_factory=utc_now)
