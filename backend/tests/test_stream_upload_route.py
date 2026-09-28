"""HTTP-boundary tests for the raw staged EEG upload contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from backend.app.api.uploads import stage_upload


def make_request(body: bytes, content_type: str) -> Request:
    """Create a synthetic ASGI request without persisting its payload."""

    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/uploads/drafts",
            "raw_path": b"/api/uploads/drafts",
            "query_string": b"",
            "headers": [
                (b"content-type", content_type.encode("ascii")),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        },
        receive,
    )


class StagedUploadRouteContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_raw_octet_stream_is_consumed_and_staged(self) -> None:
        body = b"synthetic-archive-bytes"
        consumed = bytearray()
        now = datetime.now(timezone.utc)
        draft = SimpleNamespace(
            draft_id="UPL-SYNTHETIC",
            created_at=now,
            expires_at=now + timedelta(minutes=30),
        )

        async def create_draft(_db, _storage, upload, _expires_at, _owner_id):
            while chunk := await upload.read(4):
                consumed.extend(chunk)
            return draft

        with (
            patch("backend.app.api.uploads.SessionStorage"),
            patch("backend.app.api.uploads.cleanup_expired_drafts"),
            patch(
                "backend.app.api.uploads.create_upload_draft",
                new=AsyncMock(side_effect=create_draft),
            ),
        ):
            response = await stage_upload(
                make_request(body, "application/octet-stream"),
                db=None,
                current_user=None,
            )

        self.assertEqual(response["draft_id"], "UPL-SYNTHETIC")
        self.assertEqual(consumed, body)

    async def test_multipart_archive_is_rejected_before_storage(self) -> None:
        with (
            patch("backend.app.api.uploads.SessionStorage") as storage,
            self.assertRaises(HTTPException) as raised,
        ):
            await stage_upload(
                make_request(b"synthetic", "multipart/form-data; boundary=test"),
                db=None,
                current_user=None,
            )

        self.assertEqual(raised.exception.status_code, 415)
        storage.assert_not_called()
