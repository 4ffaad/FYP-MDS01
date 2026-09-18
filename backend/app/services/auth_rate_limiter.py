"""Small in-process admission control for local authentication endpoints."""

from __future__ import annotations

from collections import deque
import os
from threading import RLock
from time import monotonic


class AuthRateLimiter:
    """Limit authentication attempts by client address and identifier."""

    def __init__(
        self,
        *,
        window_seconds: float = 60.0,
        max_attempts: int = 30,
        max_registrations: int = 10,
        max_buckets: int = 10_000,
    ) -> None:
        if window_seconds <= 0 or max_attempts <= 0 or max_registrations <= 0 or max_buckets <= 0:
            raise ValueError("Authentication rate-limit settings must be positive.")
        self.window_seconds = window_seconds
        self.max_attempts = max_attempts
        self.max_registrations = max_registrations
        self.max_buckets = max_buckets
        self._events: dict[tuple[str, str], deque[float]] = {}
        self._lock = RLock()
        self._clock = monotonic

    def allow(self, kind: str, client_host: str, identity: str) -> bool:
        """Record one attempt and return whether both buckets remain available."""

        if kind not in {"login", "register"}:
            raise ValueError("Unknown authentication rate-limit bucket.")
        if os.getenv("APP_ENV", "development").strip().lower() == "test":
            return True
        now = self._clock()
        limit = self.max_registrations if kind == "register" else self.max_attempts
        identity_key = identity.strip().casefold()[:320]
        keys = ((kind, f"ip:{client_host}"), (kind, f"identity:{identity_key}"))
        with self._lock:
            queues = []
            for key in keys:
                queue = self._events.get(key)
                if queue is not None:
                    cutoff = now - self.window_seconds
                    while queue and queue[0] <= cutoff:
                        queue.popleft()
                    if len(queue) >= limit:
                        self._trim_buckets()
                        return False
                queues.append(queue)
            for key, queue in zip(keys, queues):
                if queue is None:
                    queue = self._events.setdefault(key, deque())
                queue.append(now)
            self._trim_buckets()
            return True

    def clear(self) -> None:
        """Clear recorded attempts, primarily for isolated test processes."""

        with self._lock:
            self._events.clear()

    def _trim_buckets(self) -> None:
        if len(self._events) <= self.max_buckets:
            return
        empty = [key for key, queue in self._events.items() if not queue]
        for key in empty:
            self._events.pop(key, None)
        while len(self._events) > self.max_buckets:
            oldest_key = min(self._events, key=lambda key: self._events[key][0])
            self._events.pop(oldest_key, None)
