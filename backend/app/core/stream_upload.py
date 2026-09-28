"""Streaming request bodies into the existing encrypted upload boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
import hashlib
import io
from typing import Any

from fastapi import UploadFile
from starlette.datastructures import Headers


VIDEO_CONTENT_TYPES = {
    "avi": "video/x-msvideo",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}


class UnsupportedRawUpload(ValueError):
    """Raised when an endpoint receives multipart instead of a raw stream."""


class RequestBodyTooLarge(Exception):
    """Raised when a streamed request exceeds its route-specific byte limit."""


def request_stream_upload(
    request: Any, *, filename: str, content_type: str
) -> RequestStreamUpload:
    """Create a bounded reader only for raw octet-stream request bodies."""

    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/octet-stream":
        raise UnsupportedRawUpload("Upload bytes must use application/octet-stream.")
    return RequestStreamUpload(request, filename=filename, content_type=content_type)


def request_video_upload(request: Any) -> RequestStreamUpload:
    """Build a neutral video upload name from an allowlisted format header."""

    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/octet-stream":
        raise UnsupportedRawUpload("Upload bytes must use application/octet-stream.")
    extension = request.headers.get("x-video-format", "").strip().lower().lstrip(".")
    if extension not in VIDEO_CONTENT_TYPES:
        raise UnsupportedRawUpload("A supported X-Video-Format is required.")
    return RequestStreamUpload(
        request,
        filename=f"video.{extension}",
        content_type=VIDEO_CONTENT_TYPES[extension],
    )


class RequestStreamUpload(UploadFile):
    """Small UploadFile-compatible reader that never spools plaintext to disk.

    FastAPI's multipart parser creates a disk-backed spool for large files
    before route code can encrypt them. This adapter instead reads directly
    from the ASGI request stream; callers must consume it using bounded reads.
    """

    def __init__(self, request: Any, *, filename: str, content_type: str) -> None:
        super().__init__(
            io.BytesIO(),
            filename=filename,
            headers=Headers({"content-type": content_type}),
        )
        self._chunks: AsyncIterator[bytes] = request.stream().__aiter__()
        self._current_chunk = memoryview(b"")
        self._chunk_offset = 0
        self._finished = False
        self._closed = False
        self._content_digest = hashlib.sha256()

    @property
    def content_fingerprint(self) -> str | None:
        """Return a digest only after the whole request body has been consumed."""

        if not self._finished:
            return None
        return self._content_digest.hexdigest()

    async def read(self, size: int = -1) -> bytes:
        """Return at most ``size`` bytes, buffering only one bounded read."""

        if self._closed:
            raise ValueError("I/O operation on closed upload stream.")
        if size is None or size < 0:
            raise ValueError("Request upload streams require bounded reads.")
        if size == 0:
            return b""

        result = bytearray()
        while len(result) < size and not self._finished:
            if self._chunk_offset >= len(self._current_chunk):
                try:
                    chunk = await self._chunks.__anext__()
                except StopAsyncIteration:
                    self._finished = True
                    break
                self._current_chunk = memoryview(chunk)
                self._chunk_offset = 0
                if not chunk:
                    continue

            length = min(size - len(result), len(self._current_chunk) - self._chunk_offset)
            end = self._chunk_offset + length
            result.extend(self._current_chunk[self._chunk_offset : end])
            self._chunk_offset = end

        payload = bytes(result)
        if payload:
            self._content_digest.update(payload)
        return payload

    async def close(self) -> None:
        """Clear buffered plaintext and close the request-stream iterator."""

        if self._closed:
            return
        self._current_chunk = memoryview(b"")
        self._chunk_offset = 0
        self._closed = True
        self.file.close()
        close = getattr(self._chunks, "aclose", None)
        if close is not None:
            await close()
