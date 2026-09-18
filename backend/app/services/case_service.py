"""Privacy-safe case identifiers and aggregate case projections."""

from __future__ import annotations

import re
import secrets
from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from backend.app.database.models.eeg import EEGSession
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.database.repository import list_flagged_window_counts, list_recordings_for_session


CASE_ID_PATTERN = re.compile(r"^CASE-[0-9A-F]{8,16}$")


class CaseReferenceError(ValueError):
    """Raised when a requested case is malformed or outside the account."""


def new_case_id() -> str:
    """Generate an opaque identifier that contains no patient information."""

    return f"CASE-{secrets.token_hex(8).upper()}"


def legacy_case_id(identifier: str) -> str:
    """Give pre-case records a deterministic opaque grouping identifier."""

    return f"CASE-{identifier[-8:].upper()}"


def ensure_case_reference(db: Session, case_id: str | None, owner_user_id: int | None) -> None:
    """Reject malformed or cross-owner case references before creating data."""

    if case_id is None:
        return
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.fullmatch(case_id):
        raise CaseReferenceError("Case identifier is invalid.")

    eeg_statement = select(EEGSession.id).where(EEGSession.case_id == case_id)
    video_statement = select(VideoDetectionJob.id).where(VideoDetectionJob.case_id == case_id)
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)
    if db.exec(eeg_statement).first() is None and db.exec(video_statement).first() is None:
        raise CaseReferenceError("Case identifier was not found for this account.")


def list_cases(db: Session, owner_user_id: int | None = None) -> list[dict[str, Any]]:
    """Build an owner-scoped case summary from EEG and video analysis rows."""

    eeg_statement = select(EEGSession).order_by(EEGSession.created_at.desc())
    video_statement = select(VideoDetectionJob).order_by(VideoDetectionJob.created_at.desc())
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)

    eeg_sessions = list(db.exec(eeg_statement).all())
    video_jobs = list(db.exec(video_statement).all())
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "modalities": set(),
            "analysis_count": 0,
            "latest_created_at": None,
            "statuses": [],
            "flagged_interval_count": 0,
            "explanation_ready": False,
        }
    )

    for session in eeg_sessions:
        case_id = session.case_id or legacy_case_id(session.session_id)
        item = grouped[case_id]
        item["modalities"].add("eeg")
        item["analysis_count"] += 1
        item["statuses"].append(session.status.value)
        item["latest_created_at"] = max_timestamp(item["latest_created_at"], session.created_at)
        if session.id is not None:
            records = list_recordings_for_session(db, session.id, owner_user_id)
            item["flagged_interval_count"] += sum(
                list_flagged_window_counts(db, [record.id]).get(record.id, 0)
                for record in records
                if record.id is not None
            )
        item["explanation_ready"] = item["explanation_ready"] or session.status.value in {
            "completed",
            "completed_with_errors",
        }

    for job in video_jobs:
        case_id = job.case_id or legacy_case_id(job.job_id)
        item = grouped[case_id]
        item["modalities"].add("video")
        item["analysis_count"] += 1
        item["statuses"].append(job.status)
        item["latest_created_at"] = max_timestamp(item["latest_created_at"], job.created_at)
        item["explanation_ready"] = item["explanation_ready"] or job.status == "ready"

    result = []
    for case_id, item in grouped.items():
        result.append(
            {
                "case_id": case_id,
                "modalities": sorted(item["modalities"]),
                "analysis_count": item["analysis_count"],
                "latest_created_at": item["latest_created_at"].isoformat(),
                "status": summarize_status(item["statuses"]),
                "flagged_interval_count": item["flagged_interval_count"],
                "explanation_ready": item["explanation_ready"],
            }
        )
    return sorted(result, key=lambda item: item["latest_created_at"], reverse=True)


def get_case(db: Session, case_id: str, owner_user_id: int | None = None) -> dict[str, Any] | None:
    """Return one case with safe analysis history."""

    eeg_statement = select(EEGSession)
    video_statement = select(VideoDetectionJob)
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)
    sessions = list(db.exec(eeg_statement).all())
    jobs = list(db.exec(video_statement).all())
    sessions = [session for session in sessions if (session.case_id or legacy_case_id(session.session_id)) == case_id]
    jobs = [job for job in jobs if (job.case_id or legacy_case_id(job.job_id)) == case_id]
    if not sessions and not jobs:
        return None
    analyses = [
        {
            "id": session.session_id,
            "modality": "eeg",
            "status": summarize_status([session.status.value]),
            "created_at": session.created_at.isoformat(),
            "review_ready": session.status.value in {"completed", "completed_with_errors"},
        }
        for session in sessions
    ]
    analyses.extend(
        {
            "id": job.job_id,
            "modality": "video",
            "status": summarize_status([job.status]),
            "created_at": job.created_at.isoformat(),
            "review_ready": job.status == "ready",
        }
        for job in jobs
    )
    return {
        "case_id": case_id,
        "analyses": sorted(analyses, key=lambda item: item["created_at"], reverse=True),
    }


def max_timestamp(current, candidate):
    return candidate if current is None or candidate > current else current


def summarize_status(statuses: list[str]) -> str:
    """Return the most actionable status for a case summary."""

    if any(status in {"failed", "completed_with_errors", "needs_review"} for status in statuses):
        return "needs_review"
    if any(status not in {"completed", "ready", "expired"} for status in statuses):
        return "processing"
    return "complete"
