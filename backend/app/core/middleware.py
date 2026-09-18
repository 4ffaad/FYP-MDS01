"""ASGI middleware for rejecting oversized upload requests early."""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.core.config import MAX_UPLOAD_BYTES, MAX_VIDEO_UPLOAD_BYTES


REQUEST_BODY_OVERHEAD_BYTES = 1024 * 1024
_AUTH_BODY_LIMIT_BYTES = 1024 * 1024


class _RequestBodyTooLarge(Exception):
    """Raised when a streamed request exceeds its route-specific limit."""


class RequestBodyLimitMiddleware:
    """Reject upload bodies before Starlette parses multipart form data.

    Upload handlers still enforce the decoded file-size limit. This middleware
    additionally bounds the complete HTTP body, including multipart overhead,
    so a client cannot make the form parser consume an unbounded request first.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @staticmethod
    def _limit_for(scope: Scope) -> int | None:
        path = scope.get("path", "")
        if path in {"/api/sessions/upload", "/api/uploads/drafts"}:
            return MAX_UPLOAD_BYTES + REQUEST_BODY_OVERHEAD_BYTES
        if path in {"/api/video-detection/jobs", "/api/video-privacy/jobs"}:
            return MAX_VIDEO_UPLOAD_BYTES + REQUEST_BODY_OVERHEAD_BYTES
        if path in {"/api/auth/register", "/api/auth/login"}:
            return _AUTH_BODY_LIMIT_BYTES
        return None

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        limit = self._limit_for(scope)
        if limit is None:
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > limit:
            await JSONResponse(
                {"detail": "Request body exceeds the configured upload limit."},
                status_code=413,
            )(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            await JSONResponse(
                {"detail": "Request body exceeds the configured upload limit."},
                status_code=413,
            )(scope, receive, send)
