"""SQLModel table definitions."""

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
from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
)

__all__ = [
    "AnalysisStatus",
    "EEGRecording",
    "EEGSession",
    "Explanation",
    "Prediction",
    "ProcessingAttempt",
    "ProcessingStage",
    "ProcessingStatus",
    "RecordingStatus",
    "UploadDraft",
    "VideoPrivacyJob",
    "VideoPrivacyProfile",
    "VideoPrivacyStatus",
]
