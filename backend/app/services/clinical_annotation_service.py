"""Encrypt and validate owner-authored EEG review observations."""

from __future__ import annotations

import json
import math
import secrets
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlmodel import Session

from backend.app.core.config import STORAGE_KEY_ENV
from backend.app.database.models.clinical_annotation import ClinicalAnnotation
from backend.app.database.models.eeg import EEGRecording
from backend.app.database.repository import (
    delete_clinical_annotation,
    get_clinical_annotation,
    list_clinical_annotations,
    save_clinical_annotation,
)
from backend.app.privacy.crypto import CryptoError, read_base64_key


OBSERVATION_TYPES = frozenset(
    {
        "left_arm_movement",
        "right_arm_movement",
        "left_leg_movement",
        "right_leg_movement",
        "bilateral_movement",
        "head_or_eye_deviation",
        "other_observed_behavior",
        "uncertain_or_unobservable",
    }
)
_CRYPTO_VERSION = 1
_NONCE_BYTES = 12
_MAX_DESCRIPTION_CHARS = 4_000


class ClinicalAnnotationCryptoError(RuntimeError):
    """Configured authenticated encryption is unavailable or invalid."""


def _annotation_key() -> bytes:
    try:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"mds01-clinical-annotation-v1",
            info=b"clinical-annotation/aes-gcm",
        ).derive(read_base64_key(STORAGE_KEY_ENV))
    except (CryptoError, ValueError) as exc:
        raise ClinicalAnnotationCryptoError(
            "Clinical annotation encryption is unavailable."
        ) from exc


def _associated_data(owner_id: int, recording_db_id: int, annotation_id: str) -> bytes:
    return (
        f"mds01-clinical-annotation\0{_CRYPTO_VERSION}\0{owner_id}"
        f"\0{recording_db_id}\0{annotation_id}"
    ).encode("utf-8")


def _validated_payload(
    start_seconds: float,
    end_seconds: float,
    observations: list[str],
    description: str,
    duration_seconds: float | None,
) -> dict[str, Any]:
    if duration_seconds is not None and (
        not math.isfinite(duration_seconds) or duration_seconds <= 0
    ):
        raise ValueError("Recording duration is unavailable.")
    if (
        not math.isfinite(start_seconds)
        or not math.isfinite(end_seconds)
        or start_seconds < 0
        or end_seconds <= start_seconds
        or (
            duration_seconds is not None
            and end_seconds > duration_seconds + 1e-6
        )
    ):
        raise ValueError("Annotation times must be an interval within this recording.")
    if (
        not isinstance(observations, list)
        or len(observations) > len(OBSERVATION_TYPES)
        or any(not isinstance(item, str) or item not in OBSERVATION_TYPES for item in observations)
    ):
        raise ValueError("Select valid observation types.")
    if len(set(observations)) != len(observations):
        raise ValueError("Observation types cannot be repeated.")
    if (
        not isinstance(description, str)
        or len(description) > _MAX_DESCRIPTION_CHARS
        or any(ord(ch) < 32 and ch not in "\t\r\n" for ch in description)
    ):
        raise ValueError("Observation text is invalid or too long.")
    normalized_description = description.strip()
    if not observations and not normalized_description:
        raise ValueError("Add an observation type or a description.")
    return {
        "start_seconds": float(start_seconds),
        "end_seconds": float(end_seconds),
        "observations": observations,
        "description": normalized_description,
    }


def _encrypt_payload(
    owner_id: int, recording_db_id: int, annotation_id: str, payload: dict[str, Any]
) -> tuple[bytes, bytes]:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    ciphertext = AESGCM(_annotation_key()).encrypt(
        nonce, encoded, _associated_data(owner_id, recording_db_id, annotation_id)
    )
    return nonce, ciphertext


def _decrypt_payload(annotation: ClinicalAnnotation) -> dict[str, Any]:
    if annotation.crypto_version != _CRYPTO_VERSION or len(annotation.payload_nonce) != _NONCE_BYTES:
        raise ClinicalAnnotationCryptoError("Clinical annotation is unavailable.")
    try:
        plaintext = AESGCM(_annotation_key()).decrypt(
            annotation.payload_nonce,
            annotation.payload_ciphertext,
            _associated_data(
                annotation.owner_user_id,
                annotation.recording_db_id,
                annotation.annotation_id,
            ),
        )
        payload = json.loads(plaintext.decode("utf-8"))
        if (
            not isinstance(payload, dict)
            or set(payload) != {"start_seconds", "end_seconds", "observations", "description"}
        ):
            raise ValueError("Invalid annotation payload")
        return _validated_payload(
            payload["start_seconds"],
            payload["end_seconds"],
            payload["observations"],
            payload["description"],
            None,
        )
    except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ClinicalAnnotationCryptoError(
            "Clinical annotation is unavailable."
        ) from exc


def create_annotation(
    db: Session,
    *,
    record: EEGRecording,
    owner_user_id: int,
    annotator_user_id: int,
    start_seconds: float,
    end_seconds: float,
    observations: list[str],
    description: str,
) -> dict[str, Any]:
    payload = _validated_payload(
        start_seconds,
        end_seconds,
        observations,
        description,
        record.duration_seconds,
    )
    if record.id is None:
        raise ValueError("Recording is unavailable.")
    annotation_id = f"ANN-{uuid4().hex}"
    nonce, ciphertext = _encrypt_payload(
        owner_user_id, record.id, annotation_id, payload
    )
    annotation = save_clinical_annotation(
        db,
        ClinicalAnnotation(
            annotation_id=annotation_id,
            recording_db_id=record.id,
            owner_user_id=owner_user_id,
            created_by_user_id=annotator_user_id,
            payload_nonce=nonce,
            payload_ciphertext=ciphertext,
            crypto_version=_CRYPTO_VERSION,
        ),
    )
    return serialize_annotation(annotation)


def annotations_for_recording(
    db: Session, *, record: EEGRecording, owner_user_id: int
) -> list[dict[str, Any]]:
    if record.id is None:
        return []
    return [
        serialize_annotation(item)
        for item in list_clinical_annotations(db, record.id, owner_user_id)
    ]


def serialize_annotation(annotation: ClinicalAnnotation) -> dict[str, Any]:
    return {
        "annotation_id": annotation.annotation_id,
        "provenance": "clinician_observation",
        "annotator": "authenticated owner",
        "created_at": annotation.created_at.isoformat(),
        **_decrypt_payload(annotation),
    }


def remove_annotation(
    db: Session, *, annotation_id: str, owner_user_id: int, annotator_user_id: int
) -> bool:
    annotation = get_clinical_annotation(db, annotation_id, owner_user_id)
    if annotation is None or annotation.created_by_user_id != annotator_user_id:
        return False
    delete_clinical_annotation(db, annotation)
    return True
