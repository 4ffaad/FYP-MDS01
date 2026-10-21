"""Persist a minimal owner-scoped audit event without request or patient data."""

from sqlmodel import Session

from backend.app.database.models.clinical_access_event import ClinicalAccessEvent

_ACTIONS = {
    "recording_view",
    "prediction_view",
    "annotation_view",
    "explanation_view",
    "waveform_view",
    "recording_download",
    "session_archive_download",
    "session_report_download",
    "video_result_view",
    "video_stream",
    "video_playback_prepare",
    "video_download",
    "clinical_observation_view",
    "clinical_observation_create",
    "clinical_observation_delete",
}


def record_clinical_access(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    recording_db_id: int | None = None,
    session_db_id: int | None = None,
    video_job_db_id: int | None = None,
) -> None:
    """Commit one allowlisted access event linked only by internal row IDs."""

    if action not in _ACTIONS:
        raise ValueError("Unsupported clinical access action.")
    if sum(value is not None for value in (recording_db_id, session_db_id, video_job_db_id)) != 1:
        raise ValueError("Exactly one clinical resource must be audited.")
    db.add(
        ClinicalAccessEvent(
            actor_user_id=actor_user_id,
            action=action,
            recording_db_id=recording_db_id,
            session_db_id=session_db_id,
            video_job_db_id=video_job_db_id,
        )
    )
    db.commit()
