"""Owner-scoped, privacy-safe case summaries."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.app.core.security import owner_id, require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.services.case_service import get_case, list_cases

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def get_cases(
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> list[dict]:
    """Return case summaries without patient references, filenames, or paths."""

    return list_cases(db, owner_id(current_user))


@router.get("/{case_id}")
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_session),
    current_user: User | None = Depends(require_api_auth),
) -> dict:
    """Return one owner-scoped case history using opaque identifiers only."""

    case = get_case(db, case_id, owner_id(current_user))
    if case is None:
        raise HTTPException(status_code=404, detail="Case was not found.")
    return case
