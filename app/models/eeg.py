"""Persistent records for EEG sessions, EDF segments, and model results."""

from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecordingStatus(str, Enum):
    UPLOADED = "uploaded"
    DEIDENTIFIED = "deidentified"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class EEGSession(SQLModel, table=True):
    """A monitoring session that can contain multiple EDF recording files."""

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    # This is an opaque clinical-system reference, not a patient name.
    patient_reference: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class EEGRecording(SQLModel, table=True):
    """One variable-duration EDF file within an EEG session."""

    id: int | None = Field(default=None, primary_key=True)
    record_id: str = Field(index=True, unique=True)
    session_db_id: int = Field(foreign_key="eegsession.id", index=True)
    sequence_index: int = Field(default=1, ge=1)
    original_filename: str
    deidentified_path: str | None = None
    preprocessed_path: str | None = None
    duration_seconds: float | None = None
    sampling_rate: int | None = None
    channel_count: int | None = None
    status: RecordingStatus = Field(default=RecordingStatus.UPLOADED, index=True)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EEGWindowResult(SQLModel, table=True):
    """A future model prediction for a time window in one recording."""

    id: int | None = Field(default=None, primary_key=True)
    recording_db_id: int = Field(foreign_key="eegrecording.id", index=True)
    start_seconds: float
    end_seconds: float
    prediction: str
    confidence: float
    model_version: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
