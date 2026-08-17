"""Health endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight liveness response for the HTTP process.

    Returns
    -------
    dict[str, str]
        A constant service/status payload. This endpoint does not prove that
        PostgreSQL or a background task is healthy.
    """

    return {"status": "ok", "service": "backend"}
