"""Owner-authorized clinical observation endpoints for EEG review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.app.core.security import require_owner_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.repository import get_recording_by_public_id
from backend.app.services.clinical_annotation_service import (
    ClinicalAnnotationCryptoError,
    OBSERVATION_TYPES,
    annotations_for_recording,
    create_annotation,
    remove_annotation,
)
from backend.app.services.clinical_access_audit import record_clinical_access


router = APIRouter(prefix="/api/recordings", tags=["clinical annotations"])


class ClinicalAnnotationInput(BaseModel):
    start_seconds: float
    end_seconds: float
    observations: list[str] = Field(max_length=8)
    description: str = Field(default="", max_length=4_000)


def _record(db: Session, record_id: str, owner_id: int):
    record = get_recording_by_public_id(db, record_id, owner_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Recording was not found.")
    return record


@router.get("/{record_id}/clinical-annotations")
def list_annotations(
    record_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_owner_auth),
) -> dict:
    record = _record(db, record_id, current_user.id)
    try:
        if record.id is not None:
            record_clinical_access(
                db,
                actor_user_id=current_user.id,
                recording_db_id=record.id,
                action="clinical_observation_view",
            )
        return {
            "record_id": record.record_id,
            "annotations": annotations_for_recording(
                db, record=record, owner_user_id=current_user.id
            ),
            "observation_types": sorted(OBSERVATION_TYPES),
            "clinical_interpretation": "Observations only; not a diagnosis or seizure-onset localization.",
        }
    except ClinicalAnnotationCryptoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{record_id}/clinical-annotations", status_code=201)
def add_annotation(
    record_id: str,
    body: ClinicalAnnotationInput,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_owner_auth),
) -> dict:
    record = _record(db, record_id, current_user.id)
    try:
        annotation = create_annotation(
            db,
            record=record,
            owner_user_id=current_user.id,
            annotator_user_id=current_user.id,
            start_seconds=body.start_seconds,
            end_seconds=body.end_seconds,
            observations=body.observations,
            description=body.description,
        )
        if record.id is not None:
            record_clinical_access(
                db,
                actor_user_id=current_user.id,
                recording_db_id=record.id,
                action="clinical_observation_create",
            )
        return {"record_id": record.record_id, "annotation": annotation}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClinicalAnnotationCryptoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{record_id}/clinical-annotations/{annotation_id}", status_code=204)
def delete_annotation(
    record_id: str,
    annotation_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_owner_auth),
) -> None:
    record = _record(db, record_id, current_user.id)
    if not remove_annotation(
        db,
        annotation_id=annotation_id,
        owner_user_id=current_user.id,
        annotator_user_id=current_user.id,
    ):
        raise HTTPException(status_code=404, detail="Annotation was not found.")
    if record.id is not None:
        record_clinical_access(
            db,
            actor_user_id=current_user.id,
            recording_db_id=record.id,
            action="clinical_observation_delete",
        )
