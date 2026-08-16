"""RQ enqueueing and worker entry points."""

from __future__ import annotations

import uuid

from backend.app.core.config import REDIS_URL, RQ_QUEUE_NAME


def enqueue_pipeline(session_id: str) -> str:
    """Enqueue a session without importing Redis/RQ during API startup."""

    try:
        from redis import Redis
        from rq import Queue
        from rq.job import Retry
    except ImportError as exc:  # pragma: no cover - exercised in minimal envs
        raise RuntimeError("Redis/RQ dependencies are not installed.") from exc

    job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
    queue = Queue(RQ_QUEUE_NAME, connection=Redis.from_url(REDIS_URL))
    queue.enqueue(
        run_eeg_pipeline,
        session_id,
        job_id,
        job_id=job_id,
        retry=Retry(max=2, interval=[5, 30]),
    )
    return job_id


def run_eeg_pipeline(session_id: str, job_id: str) -> None:
    from backend.app.services.processing_service import process_session

    process_session(session_id, job_id)
