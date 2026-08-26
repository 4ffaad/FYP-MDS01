"""Bound concurrent in-process analyses for the prototype runtime."""

from __future__ import annotations

import os
from collections.abc import Callable
from threading import BoundedSemaphore

from backend.app.services.processing_service import process_session


class ProcessingCapacity:
    """Reserve and release a fixed number of background-processing slots."""

    def __init__(self, limit: int, processor: Callable[[str], None] = process_session) -> None:
        if limit < 1:
            raise ValueError("Processing capacity must be at least one.")
        self._semaphore = BoundedSemaphore(limit)
        self._processor = processor

    def reserve(self) -> bool:
        """Reserve a slot without blocking the HTTP request."""

        return self._semaphore.acquire(blocking=False)

    def release(self) -> None:
        """Release a previously reserved slot after setup failure."""

        self._semaphore.release()

    def run_reserved(self, session_id: str) -> None:
        """Process one reserved session and always release its slot."""

        try:
            self._processor(session_id)
        finally:
            self.release()


processing_capacity = ProcessingCapacity(int(os.getenv("MAX_CONCURRENT_ANALYSES", "1")))
