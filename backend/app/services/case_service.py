"""Privacy-safe case identifiers and aggregate case projections."""

from __future__ import annotations

import re
import secrets
from collections import defaultdict
from typing import Any, cast

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from backend.app.database.models.auth import User
from backend.app.database.models.case_profile import CasePatientProfile
from backend.app.database.models.eeg import EEGSession
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.database.models.video import VideoPrivacyJob
from backend.app.database.repository import list_flagged_window_counts, list_recordings_for_session
from backend.app.services.case_profile_service import (
    PatientProfileCryptoError,
    delete_patient_profile,
    decrypt_profile,
)


CASE_ID_PATTERN = re.compile(r"^CASE-[0-9A-F]{8,16}$")
_PATIENT_NAME_LABELS = frozenset({"name", "patient name", "full name"})
_REPORT_SUMMARY_LABELS = frozenset({"conclusion", "conclusions", "impression"})
_CONTACT_IN_SUMMARY = re.compile(
    r"(?:@|\b(?:phone|telephone|mobile|contact|address|street|road|avenue|postcode|postal code|unit|block|district|city|jalan|kampung)\b|\+?\d[\d(). -]{7,}\d)",
    re.IGNORECASE,
)


class CaseReferenceError(ValueError):
    """Raised when a requested case is malformed or outside the account."""


def lock_owner_case_mutations(db: Session, owner_user_id: int | None) -> None:
    """Serialize one owner's case creation, attachment, and final deletion."""

    if owner_user_id is None:
        return
    user = db.exec(
        select(User)
        .where(User.id == owner_user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if user is None:
        return


def cleanup_case_profile_if_empty(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int | None,
) -> bool:
    """Delete encrypted identity only while the owner-locked case is empty."""

    if owner_user_id is None:
        return False
    lock_owner_case_mutations(db, owner_user_id)
    if get_case(db, case_id, owner_user_id) is not None:
        return False
    delete_patient_profile(db, case_id=case_id, owner_user_id=owner_user_id)
    return True


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
    privacy_statement = select(VideoPrivacyJob.id).where(VideoPrivacyJob.case_id == case_id)
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)
        privacy_statement = privacy_statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    if (
        db.exec(eeg_statement).first() is None
        and db.exec(video_statement).first() is None
        and db.exec(privacy_statement).first() is None
    ):
        raise CaseReferenceError("Case identifier was not found for this account.")


def list_cases(
    db: Session,
    owner_user_id: int | None = None,
    *,
    profile_owner_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Build an owner-scoped case summary from EEG and video analysis rows."""

    eeg_statement = select(EEGSession).order_by(EEGSession.created_at.desc())
    video_statement = select(VideoDetectionJob).order_by(VideoDetectionJob.created_at.desc())
    privacy_statement = select(VideoPrivacyJob)
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)
        privacy_statement = privacy_statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)

    eeg_sessions = list(db.exec(eeg_statement).all())
    video_jobs = list(db.exec(video_statement).all())
    privacy_jobs = list(db.exec(privacy_statement).all())
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "modalities": set(),
            "analysis_count": 0,
            "privacy_preview_count": 0,
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

    for job in privacy_jobs:
        case_id = job.case_id or legacy_case_id(job.job_id)
        item = grouped[case_id]
        item["modalities"].add("video")
        item["privacy_preview_count"] += 1
        item["statuses"].append(getattr(job.status, "value", str(job.status)))
        item["latest_created_at"] = max_timestamp(item["latest_created_at"], job.created_at)

    summary_owner = (
        profile_owner_user_id if profile_owner_user_id is not None else owner_user_id
    )
    projections = _patient_summaries_for_cases(db, grouped.keys(), summary_owner)
    result = []
    for case_id, item in grouped.items():
        patient = projections.get(case_id, {})
        result.append(
            {
                "case_id": case_id,
                "patient_name": patient.get("patient_name"),
                "report_summary": patient.get("report_summary"),
                "modalities": sorted(item["modalities"]),
                "analysis_count": item["analysis_count"],
                "privacy_preview_count": item["privacy_preview_count"],
                "latest_created_at": item["latest_created_at"].isoformat(),
                "status": summarize_status(item["statuses"]),
                "flagged_interval_count": item["flagged_interval_count"],
                "explanation_ready": item["explanation_ready"],
            }
        )
    return sorted(result, key=lambda item: item["latest_created_at"], reverse=True)


def _patient_summaries_for_cases(
    db: Session,
    case_ids,
    owner_user_id: int | None,
) -> dict[str, dict[str, str | None]]:
    """Decrypt only owner-scoped name and allow-listed conclusion previews."""

    if owner_user_id is None:
        return {}
    identifiers = list(case_ids)
    if not identifiers:
        return {}
    case_id_column = cast(Any, CasePatientProfile.case_id)
    profiles = db.exec(
        select(CasePatientProfile).where(
            CasePatientProfile.owner_user_id == owner_user_id,
            case_id_column.in_(identifiers),
        )
    ).all()
    summaries: dict[str, dict[str, str | None]] = {}
    for row in profiles:
        try:
            profile = decrypt_profile(
                row.owner_user_id,
                row.case_id,
                row.identity_nonce,
                row.identity_ciphertext,
                version=row.crypto_version,
            )
        except PatientProfileCryptoError:
            continue
        details = profile.get("details", [])
        patient_name = profile.get("name", "").strip()
        if not patient_name and isinstance(details, list):
            patient_name = next(
                (
                    detail.get("value", "").strip()
                    for detail in details
                    if isinstance(detail, dict)
                    and _normalized_label(detail.get("label", "")) in _PATIENT_NAME_LABELS
                    and isinstance(detail.get("value"), str)
                ),
                "",
            )
        if _CONTACT_IN_SUMMARY.search(patient_name):
            patient_name = ""
        report_summary = ""
        if isinstance(details, list):
            report_summary = next(
                (
                    detail["value"].strip()
                    for detail in details
                    if isinstance(detail, dict)
                    and _normalized_label(detail.get("label", ""))
                    in _REPORT_SUMMARY_LABELS
                    and isinstance(detail.get("value"), str)
                    and detail["value"].strip()
                    and not _CONTACT_IN_SUMMARY.search(detail["value"])
                ),
                "",
            )
        if len(report_summary) > 280:
            report_summary = report_summary[:277].rstrip() + "…"
        summaries[row.case_id] = {
            "patient_name": patient_name[:160] or None,
            "report_summary": report_summary or None,
        }
    return summaries


def _normalized_label(label: object) -> str:
    if not isinstance(label, str):
        return ""
    return " ".join(label.strip().strip(":").split()).casefold()


def get_case(
    db: Session,
    case_id: str,
    owner_user_id: int | None = None,
    *,
    profile_owner_user_id: int | None = None,
) -> dict[str, Any] | None:
    """Return one case with safe analysis history."""

    if not CASE_ID_PATTERN.fullmatch(case_id):
        return None
    case_suffix = case_id[-8:]
    eeg_case_column = cast(Any, EEGSession.case_id)
    eeg_id_column = cast(Any, EEGSession.session_id)
    video_case_column = cast(Any, VideoDetectionJob.case_id)
    video_id_column = cast(Any, VideoDetectionJob.job_id)
    privacy_case_column = cast(Any, VideoPrivacyJob.case_id)
    privacy_id_column = cast(Any, VideoPrivacyJob.job_id)
    eeg_statement = select(EEGSession).where(
        or_(
            eeg_case_column == case_id,
            and_(eeg_case_column.is_(None), eeg_id_column.endswith(case_suffix)),
        )
    )
    video_statement = select(VideoDetectionJob).where(
        or_(
            video_case_column == case_id,
            and_(video_case_column.is_(None), video_id_column.endswith(case_suffix)),
        )
    )
    privacy_statement = select(VideoPrivacyJob).where(
        or_(
            privacy_case_column == case_id,
            and_(privacy_case_column.is_(None), privacy_id_column.endswith(case_suffix)),
        )
    )
    if owner_user_id is not None:
        eeg_statement = eeg_statement.where(EEGSession.owner_user_id == owner_user_id)
        video_statement = video_statement.where(VideoDetectionJob.owner_user_id == owner_user_id)
        privacy_statement = privacy_statement.where(VideoPrivacyJob.owner_user_id == owner_user_id)
    sessions = list(db.exec(eeg_statement).all())
    jobs = list(db.exec(video_statement).all())
    privacy_jobs = list(db.exec(privacy_statement).all())
    if not sessions and not jobs and not privacy_jobs:
        return None
    summary_owner = (
        profile_owner_user_id if profile_owner_user_id is not None else owner_user_id
    )
    patient = _patient_summaries_for_cases(db, [case_id], summary_owner).get(case_id, {})
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
        "patient_name": patient.get("patient_name"),
        "report_summary": patient.get("report_summary"),
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
