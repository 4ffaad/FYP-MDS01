"""Owner-scoped case summaries and separately protected patient identity."""

import json
import re
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import Session

from backend.app.core.security import owner_id, require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.api.upload_contracts import pdf_upload_openapi
from backend.app.services.case_service import (
    get_case,
    list_cases,
    lock_owner_case_mutations,
)
from backend.app.services.case_profile_service import (
    PatientProfileCryptoError,
    ReviewedPatientProfileConflict,
    delete_patient_profile,
    load_patient_profile,
    save_extracted_patient_profile,
    save_patient_profile,
)
from backend.app.services.case_source_report_service import (
    MAX_CASE_SOURCE_REPORT_BYTES,
    CaseSourceReportError,
    InvalidCaseSourceReport,
    delete_case_source_report,
    load_case_source_report,
    save_case_source_report,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])
_MAX_PROFILE_BODY_BYTES = 128 * 1024
_MAX_PROFILE_FINDINGS_CHARS = 8_000
_MAX_PROFILE_DETAIL_COUNT = 80
_MAX_PROFILE_DETAIL_LABEL_CHARS = 80
_MAX_PROFILE_DETAIL_VALUE_CHARS = 6_000
_MAX_PROFILE_DETAIL_CHARS = 25_000
_SOURCE_REPORT_UPLOAD_SLOTS = BoundedSemaphore(1)
_AGE_VALUE = re.compile(
    r"^(?P<value>\d{1,3}(?:\.\d)?)\s*(?:(?:years?|yrs?)(?:\s+old)?|months?|mos?)?$",
    re.IGNORECASE,
)


def _is_valid_age(value: str) -> bool:
    match = _AGE_VALUE.fullmatch(value.strip())
    return match is not None and float(match.group("value")) <= 150


def _validated_details(value: object) -> list[dict[str, str]]:
    """Validate a bounded list of patient/report fields before encryption."""

    if not isinstance(value, list) or not value or len(value) > _MAX_PROFILE_DETAIL_COUNT:
        raise ValueError("Invalid patient details.")
    details: list[dict[str, str]] = []
    total_chars = 0
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"label", "value"}:
            raise ValueError("Invalid patient detail.")
        label = entry["label"]
        detail_value = entry["value"]
        if (
            not isinstance(label, str)
            or not isinstance(detail_value, str)
            or not label.strip()
            or not detail_value.strip()
            or len(label) > _MAX_PROFILE_DETAIL_LABEL_CHARS
            or len(detail_value) > _MAX_PROFILE_DETAIL_VALUE_CHARS
            or any(ord(character) < 32 and character not in "\t\r\n" for character in label)
            or any(ord(character) < 32 and character not in "\t\r\n" for character in detail_value)
        ):
            raise ValueError("Invalid patient detail.")
        normalized = {"label": label.strip(), "value": detail_value.strip()}
        if re.search(r"\bage\b", normalized["label"], re.IGNORECASE) and not _is_valid_age(
            normalized["value"]
        ):
            raise ValueError("Age must be a numeric age, not a date of birth.")
        total_chars += len(normalized["label"]) + len(normalized["value"])
        if total_chars > _MAX_PROFILE_DETAIL_CHARS:
            raise ValueError("Patient details exceed the size limit.")
        details.append(normalized)
    return details


@router.get("")
def get_cases(
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> list[dict]:
    """Return case summaries without patient references, filenames, or paths."""

    return list_cases(
        db,
        owner_id(current_user),
        profile_owner_user_id=current_user.id if current_user is not None else None,
    )


@router.get("/{case_id}")
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return one owner-scoped case history using opaque identifiers only."""

    case = get_case(
        db,
        case_id,
        owner_id(current_user),
        profile_owner_user_id=current_user.id if current_user is not None else None,
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case was not found.")
    return case


def _profile_owner(user: User | None) -> int:
    """Require an authenticated account; admin-wide read scopes never apply."""

    if user is None or user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user.id


def _require_owned_case(db: Session, case_id: str, owner_user_id: int) -> None:
    if get_case(db, case_id, owner_user_id) is None:
        raise HTTPException(status_code=404, detail="Case was not found.")


async def _bounded_source_report_body(request: Request) -> bytes:
    """Read only a bounded raw PDF body without reflecting submitted bytes."""

    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Submit a PDF source report.")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid request size.") from exc
        if declared_length < 0:
            raise HTTPException(status_code=400, detail="Invalid request size.")
        if declared_length > MAX_CASE_SOURCE_REPORT_BYTES:
            raise HTTPException(status_code=413, detail="Source report exceeds the size limit.")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_CASE_SOURCE_REPORT_BYTES:
            raise HTTPException(status_code=413, detail="Source report exceeds the size limit.")
        body.extend(chunk)
    return bytes(body)


@router.get("/{case_id}/patient-profile")
def get_patient_profile(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return only the authenticated owner's separately encrypted profile."""

    owner = _profile_owner(current_user)
    _require_owned_case(db, case_id, owner)
    try:
        loaded = load_patient_profile(db, case_id=case_id, owner_user_id=owner)
    except PatientProfileCryptoError as exc:
        raise HTTPException(503, "The patient profile cannot be decrypted with the configured key.") from exc
    if loaded is None:
        return {"profile": None}
    identity, row = loaded
    identity.setdefault("details", [])
    return {
        "profile": {
            **identity,
            "reviewed": row.verification_status == "reviewed",
            "verification_status": row.verification_status,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        }
    }


@router.put("/{case_id}/patient-profile/extracted")
async def put_extracted_patient_profile(
    case_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Encrypt owner-submitted extraction fields while keeping review status explicit."""

    owner = _profile_owner(current_user)
    _require_owned_case(db, case_id, owner)
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_PROFILE_BODY_BYTES:
                raise HTTPException(413, "Patient details exceed the size limit.")
        except ValueError as exc:
            raise HTTPException(400, "Invalid request size.") from exc
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > _MAX_PROFILE_BODY_BYTES:
            raise HTTPException(413, "Patient details exceed the size limit.")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(422, "Submit valid extracted patient details.") from exc
    if not isinstance(payload, dict) or set(payload) != {"details"}:
        raise HTTPException(422, "Submit only extracted patient details.")
    try:
        details = _validated_details(payload["details"])
    except ValueError as exc:
        raise HTTPException(422, "Extracted patient details are invalid.") from exc

    lock_owner_case_mutations(db, owner)
    _require_owned_case(db, case_id, owner)
    try:
        row = save_extracted_patient_profile(
            db,
            case_id=case_id,
            owner_user_id=owner,
            details=details,
        )
        loaded = load_patient_profile(db, case_id=case_id, owner_user_id=owner)
    except ReviewedPatientProfileConflict as exc:
        raise HTTPException(409, "A reviewed patient profile cannot be replaced by extraction.") from exc
    except PatientProfileCryptoError as exc:
        raise HTTPException(503, "Patient profile encryption is unavailable; no identity was saved.") from exc
    if loaded is None:
        raise HTTPException(503, "Extracted patient details are unavailable.")
    identity, row = loaded
    identity.setdefault("details", [])
    return {
        "profile": {
            **identity,
            "reviewed": False,
            "verification_status": row.verification_status,
            "reviewed_at": None,
        }
    }


@router.put("/{case_id}/patient-profile")
async def put_patient_profile(
    case_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Persist only the reviewed profile fields as authenticated ciphertext.

    The body is validated manually so validation errors never echo submitted
    patient values in FastAPI's default request-body error payload. The source
    report itself is never accepted by this endpoint.
    """

    owner = _profile_owner(current_user)
    _require_owned_case(db, case_id, owner)
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_PROFILE_BODY_BYTES:
                raise HTTPException(413, "Reviewed profile exceeds the size limit.")
        except ValueError as exc:
            raise HTTPException(400, "Invalid request size.") from exc
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > _MAX_PROFILE_BODY_BYTES:
            raise HTTPException(413, "Reviewed profile exceeds the size limit.")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(422, "Submit a valid reviewed profile.") from exc
    if not isinstance(payload, dict) or payload.get("review_confirmed") is not True:
        raise HTTPException(422, "Review the patient details before saving.")
    detail_payload = {"details", "review_confirmed"}
    legacy_required = {"name", "hospital_id", "review_confirmed"}
    legacy_accepted = (legacy_required, legacy_required | {"age", "findings"})
    if set(payload) == detail_payload:
        try:
            details = _validated_details(payload["details"])
        except ValueError as exc:
            raise HTTPException(422, "Review each patient detail before saving.") from exc
        name = hospital_id = age = findings = ""
    elif set(payload) in legacy_accepted:
        name = payload.get("name")
        hospital_id = payload.get("hospital_id")
        age = payload.get("age", "")
        findings = payload.get("findings", "")
        if (
            not isinstance(name, str)
            or not isinstance(hospital_id, str)
            or not isinstance(age, str)
            or not isinstance(findings, str)
            or not name.strip()
            or not hospital_id.strip()
            or len(age) > 32
            or (bool(age.strip()) and not _is_valid_age(age))
            or len(findings) > _MAX_PROFILE_FINDINGS_CHARS
            or len(name) > 160
            or len(hospital_id) > 80
            or any(ord(character) < 32 and character not in "\t\r\n" for character in name + hospital_id + age + findings)
        ):
            raise HTTPException(422, "Review and correct the profile fields before saving.")
        name = name.strip()
        hospital_id = hospital_id.strip()
        age = age.strip()
        findings = findings.strip()
        details = []
    else:
        raise HTTPException(422, "Submit only reviewed patient details.")
    lock_owner_case_mutations(db, owner)
    _require_owned_case(db, case_id, owner)
    try:
        row = save_patient_profile(
            db,
            case_id=case_id,
            owner_user_id=owner,
            name=name,
            hospital_id=hospital_id,
            age=age,
            findings=findings,
            details=details,
        )
    except PatientProfileCryptoError as exc:
        raise HTTPException(503, "Patient profile encryption is unavailable; no identity was saved.") from exc
    return {
        "profile": {
            "name": name,
            "hospital_id": hospital_id,
            "age": age,
            "findings": findings,
            "details": details,
            "reviewed": True,
            "verification_status": row.verification_status,
            "reviewed_at": row.reviewed_at.isoformat(),
        }
    }


@router.delete("/{case_id}/patient-profile", status_code=204)
def remove_patient_profile(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> None:
    """Delete this owner's identity while retaining de-identified analyses."""

    owner = _profile_owner(current_user)
    lock_owner_case_mutations(db, owner)
    _require_owned_case(db, case_id, owner)
    try:
        delete_patient_profile(db, case_id=case_id, owner_user_id=owner)
    except CaseSourceReportError as exc:
        raise HTTPException(503, "Patient profile cleanup is unavailable.") from exc


@router.get("/{case_id}/report")
def get_case_source_report(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> Response:
    """Return an authenticated owner's decrypted PDF without caching it."""

    owner = _profile_owner(current_user)
    _require_owned_case(db, case_id, owner)
    try:
        pdf_bytes = load_case_source_report(db, case_id=case_id, owner_user_id=owner)
    except CaseSourceReportError as exc:
        raise HTTPException(503, "The source report is unavailable.") from exc
    if pdf_bytes is None:
        raise HTTPException(404, "Source report was not found.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="source-report.pdf"',
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/{case_id}/report", status_code=204, openapi_extra=pdf_upload_openapi())
async def put_case_source_report(
    case_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> None:
    """Encrypt and atomically replace an owned case's PDF source report."""

    owner = _profile_owner(current_user)
    _require_owned_case(db, case_id, owner)
    if not _SOURCE_REPORT_UPLOAD_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "Another source report upload is in progress.")
    try:
        pdf_bytes = await _bounded_source_report_body(request)
        lock_owner_case_mutations(db, owner)
        _require_owned_case(db, case_id, owner)
        try:
            save_case_source_report(
                db,
                case_id=case_id,
                owner_user_id=owner,
                pdf_bytes=pdf_bytes,
            )
        except InvalidCaseSourceReport as exc:
            raise HTTPException(422, "Submit a valid PDF source report.") from exc
        except CaseSourceReportError as exc:
            raise HTTPException(503, "The source report could not be saved.") from exc
    finally:
        _SOURCE_REPORT_UPLOAD_SLOTS.release()


@router.delete("/{case_id}/report", status_code=204)
def remove_case_source_report(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> None:
    """Delete an owner's case report while retaining a cleanup pointer safely."""

    owner = _profile_owner(current_user)
    lock_owner_case_mutations(db, owner)
    _require_owned_case(db, case_id, owner)
    try:
        delete_case_source_report(db, case_id=case_id, owner_user_id=owner)
    except CaseSourceReportError as exc:
        raise HTTPException(503, "The source report could not be deleted.") from exc
