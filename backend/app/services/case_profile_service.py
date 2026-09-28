"""Encrypt and owner-scope patient profiles with explicit review status."""

from __future__ import annotations

import json
import re
import secrets
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlmodel import Session, select

from backend.app.core.config import STORAGE_KEY_ENV
from backend.app.database.models.case_profile import CasePatientProfile, utc_now
from backend.app.privacy.crypto import CryptoError, read_base64_key
from backend.app.services.case_source_report_service import (
    delete_case_source_report,
    stage_case_source_report_cleanup,
)


CRYPTO_VERSION = 3
_SUPPORTED_CRYPTO_VERSIONS = frozenset({1, 2, CRYPTO_VERSION})
_NONCE_BYTES = 12
_MAX_PROFILE_DETAILS = 80
_MAX_PROFILE_DETAIL_LABEL_CHARS = 80
_MAX_PROFILE_DETAIL_VALUE_CHARS = 6_000
_MAX_PROFILE_DETAIL_CHARS = 25_000


class PatientProfileCryptoError(RuntimeError):
    """Raised when identity encryption or authenticated decryption fails."""


class ReviewedPatientProfileConflict(RuntimeError):
    """Raised when an automatic extraction would replace reviewed data."""


def _profile_key(version: int = CRYPTO_VERSION) -> bytes:
    """Derive a domain-separated profile key from the configured storage key."""

    if version not in _SUPPORTED_CRYPTO_VERSIONS:
        raise PatientProfileCryptoError("Patient profile encryption is unavailable.")
    try:
        master_key = read_base64_key(STORAGE_KEY_ENV)
        salt = f"mds01-case-patient-profile-v{version}".encode("ascii")
        info = (
            b"case-patient-profile/aes-gcm"
            if version == 1
            else f"case-patient-profile/v{version}/aes-gcm".encode("ascii")
        )
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
        ).derive(master_key)
    except (CryptoError, ValueError) as exc:
        raise PatientProfileCryptoError("Patient profile encryption is unavailable.") from exc


def _associated_data(owner_user_id: int, case_id: str, version: int) -> bytes:
    return f"mds01-case-profile\0{version}\0{owner_user_id}\0{case_id}".encode("utf-8")


def _validated_details(details: object) -> list[dict[str, str]]:
    """Validate bounded report fields before encryption."""

    if not isinstance(details, list) or len(details) > _MAX_PROFILE_DETAILS:
        raise ValueError("Invalid patient report details.")
    output: list[dict[str, str]] = []
    total_chars = 0
    for detail in details:
        if not isinstance(detail, dict) or set(detail) != {"label", "value"}:
            raise ValueError("Invalid patient report detail.")
        label = detail["label"]
        value = detail["value"]
        if (
            not isinstance(label, str)
            or not isinstance(value, str)
            or not label.strip()
            or not value.strip()
            or len(label) > _MAX_PROFILE_DETAIL_LABEL_CHARS
            or len(value) > _MAX_PROFILE_DETAIL_VALUE_CHARS
            or any(ord(character) < 32 and character not in "\t\r\n" for character in label)
            or any(ord(character) < 32 and character not in "\t\r\n" for character in value)
        ):
            raise ValueError("Invalid patient report detail.")
        normalized = {"label": label.strip(), "value": value.strip()}
        total_chars += len(normalized["label"]) + len(normalized["value"])
        if total_chars > _MAX_PROFILE_DETAIL_CHARS:
            raise ValueError("Patient report details exceed the size limit.")
        output.append(normalized)
    return output


def encrypt_profile(
    owner_user_id: int,
    case_id: str,
    profile: dict[str, Any],
) -> tuple[bytes, bytes]:
    """Return a fresh AES-GCM nonce and authenticated ciphertext."""

    try:
        encrypted_profile = {
            "age": profile.get("age", ""),
            "findings": profile.get("findings", ""),
            "hospital_id": profile.get("hospital_id", ""),
            "name": profile.get("name", ""),
        }
        if "details" in profile:
            encrypted_profile["details"] = _validated_details(profile["details"])
        if not all(
            isinstance(encrypted_profile[key], str)
            for key in ("age", "findings", "hospital_id", "name")
        ):
            raise ValueError("Invalid patient profile.")
        plaintext = json.dumps(
            encrypted_profile,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ciphertext = AESGCM(_profile_key()).encrypt(
            nonce, plaintext, _associated_data(owner_user_id, case_id, CRYPTO_VERSION)
        )
        return nonce, ciphertext
    except PatientProfileCryptoError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise PatientProfileCryptoError("Patient profile could not be encrypted.") from exc


def decrypt_profile(
    owner_user_id: int,
    case_id: str,
    nonce: bytes,
    ciphertext: bytes,
    version: int = CRYPTO_VERSION,
) -> dict[str, Any]:
    """Authenticate and decrypt a profile only for its bound owner and case."""

    if len(nonce) != _NONCE_BYTES:
        raise PatientProfileCryptoError("Patient profile is unavailable.")
    try:
        plaintext = AESGCM(_profile_key(version)).decrypt(
            nonce, ciphertext, _associated_data(owner_user_id, case_id, version)
        )
        profile = json.loads(plaintext.decode("utf-8"))
        fields = {"name", "hospital_id"} if version == 1 else {
            "name", "hospital_id", "age", "findings"
        }
        if version >= 3 and "details" in profile:
            fields = fields | {"details"}
        if (
            not isinstance(profile, dict)
            or set(profile) != fields
            or not all(isinstance(profile[key], str) for key in fields - {"details"})
        ):
            raise ValueError("Invalid patient profile payload.")
        result: dict[str, Any] = {
            "name": profile["name"],
            "hospital_id": profile["hospital_id"],
            "age": profile.get("age", ""),
            "findings": profile.get("findings", ""),
        }
        if "details" in profile:
            result["details"] = _validated_details(profile["details"])
        return result
    except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PatientProfileCryptoError("Patient profile is unavailable.") from exc


def save_patient_profile(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
    name: str,
    hospital_id: str,
    age: str = "",
    findings: str = "",
    details: list[dict[str, str]] | None = None,
) -> CasePatientProfile:
    """Encrypt and upsert patient fields after an explicit review."""

    nonce, ciphertext = encrypt_profile(
        owner_user_id,
        case_id,
        {
            "name": name,
            "hospital_id": hospital_id,
            "age": age,
            "findings": findings,
            "details": details or [],
        },
    )
    profile = db.exec(
        select(CasePatientProfile).where(
            CasePatientProfile.case_id == case_id,
            CasePatientProfile.owner_user_id == owner_user_id,
        )
    ).first()
    now = utc_now()
    if profile is None:
        profile = CasePatientProfile(
            case_id=case_id,
            owner_user_id=owner_user_id,
            identity_nonce=nonce,
            identity_ciphertext=ciphertext,
            crypto_version=CRYPTO_VERSION,
            verification_status="reviewed",
            reviewed_by_user_id=owner_user_id,
            reviewed_at=now,
            created_at=now,
            updated_at=now,
        )
    else:
        profile.identity_nonce = nonce
        profile.identity_ciphertext = ciphertext
        profile.crypto_version = CRYPTO_VERSION
        profile.verification_status = "reviewed"
        profile.reviewed_by_user_id = owner_user_id
        profile.reviewed_at = now
        profile.updated_at = now
    db.add(profile)
    try:
        db.commit()
        db.refresh(profile)
    except Exception:
        db.rollback()
        raise
    return profile


def save_extracted_patient_profile(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
    details: list[dict[str, str]],
) -> CasePatientProfile:
    """Encrypt auto-extracted report fields without marking them reviewed."""

    validated_details = _validated_details(details)
    if not validated_details:
        raise ValueError("At least one extracted patient detail is required.")
    values = {
        re.sub(r"[^a-z0-9]+", " ", item["label"].casefold()).strip(): item[
            "value"
        ].strip()
        for item in validated_details
    }
    name = values.get("patient name") or values.get("name of patient") or ""
    hospital_id = next(
        (
            values[label]
            for label in (
                "hospital id",
                "hospital number",
                "hospital no",
                "medical record number",
                "medical record no",
                "medical record id",
                "mrn",
            )
            if values.get(label)
        ),
        "",
    )
    nonce, ciphertext = encrypt_profile(
        owner_user_id,
        case_id,
        {
            "name": name,
            "hospital_id": hospital_id,
            "age": "",
            "findings": "",
            "details": validated_details,
        },
    )
    profile = db.exec(
        select(CasePatientProfile).where(
            CasePatientProfile.case_id == case_id,
            CasePatientProfile.owner_user_id == owner_user_id,
        )
    ).first()
    if profile is not None and profile.verification_status == "reviewed":
        raise ReviewedPatientProfileConflict(
            "An extracted report cannot replace an already reviewed patient profile."
        )

    now = utc_now()
    if profile is None:
        profile = CasePatientProfile(
            case_id=case_id,
            owner_user_id=owner_user_id,
            identity_nonce=nonce,
            identity_ciphertext=ciphertext,
            crypto_version=CRYPTO_VERSION,
            verification_status="auto_extracted",
            reviewed_by_user_id=None,
            reviewed_at=None,
            created_at=now,
            updated_at=now,
        )
    else:
        profile.identity_nonce = nonce
        profile.identity_ciphertext = ciphertext
        profile.crypto_version = CRYPTO_VERSION
        profile.verification_status = "auto_extracted"
        profile.reviewed_by_user_id = None
        profile.reviewed_at = None
        profile.updated_at = now
    db.add(profile)
    try:
        db.commit()
        db.refresh(profile)
    except Exception:
        db.rollback()
        raise
    return profile


def load_patient_profile(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
) -> tuple[dict[str, Any], CasePatientProfile] | None:
    """Load and decrypt only a profile belonging to the authenticated owner."""

    profile = db.exec(
        select(CasePatientProfile).where(
            CasePatientProfile.case_id == case_id,
            CasePatientProfile.owner_user_id == owner_user_id,
        )
    ).first()
    if profile is None:
        return None
    if profile.crypto_version not in _SUPPORTED_CRYPTO_VERSIONS:
        raise PatientProfileCryptoError("Patient profile is unavailable.")
    return (
        decrypt_profile(
            owner_user_id,
            case_id,
            profile.identity_nonce,
            profile.identity_ciphertext,
            version=profile.crypto_version,
        ),
        profile,
    )


def stage_patient_profile_deletion(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
) -> bool:
    """Stage profile deletion and report tombstoning in the caller's transaction."""

    profile = db.exec(
        select(CasePatientProfile).where(
            CasePatientProfile.case_id == case_id,
            CasePatientProfile.owner_user_id == owner_user_id,
        )
    ).first()
    stage_case_source_report_cleanup(
        db,
        case_id=case_id,
        owner_user_id=owner_user_id,
    )
    if profile is not None:
        db.delete(profile)
    return profile is not None


def delete_patient_profile(db: Session, *, case_id: str, owner_user_id: int) -> bool:
    """Atomically delete identity and hide its report before file cleanup."""

    try:
        profile_existed = stage_patient_profile_deletion(
            db,
            case_id=case_id,
            owner_user_id=owner_user_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        delete_case_source_report(db, case_id=case_id, owner_user_id=owner_user_id)
    except Exception:
        db.rollback()
        raise
    return profile_existed
