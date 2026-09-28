"""Bounded request-body upload adapter tests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.app.core.stream_upload import RequestStreamUpload


async def chunks(*values: bytes):
    for value in values:
        yield value


class RequestStreamUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_asgi_chunk_is_not_copied_into_an_unbounded_buffer(self) -> None:
        chunk = b"x" * (4 * 1024 * 1024)
        upload = RequestStreamUpload(
            SimpleNamespace(stream=lambda: chunks(chunk)),
            filename="upload.zip",
            content_type="application/zip",
        )

        self.assertEqual(await upload.read(1024), b"x" * 1024)
        self.assertIs(upload._current_chunk.obj, chunk)
        self.assertEqual(len(upload._current_chunk), len(chunk))

        await upload.close()

    async def test_reads_stream_chunks_without_loading_the_entire_body(self) -> None:
        upload = RequestStreamUpload(
            SimpleNamespace(stream=lambda: chunks(b"ab", b"cdef")),
            filename="upload.zip",
            content_type="application/zip",
        )

        self.assertEqual(await upload.read(3), b"abc")
        self.assertEqual(await upload.read(3), b"def")
        self.assertEqual(await upload.read(3), b"")
        self.assertEqual(upload.filename, "upload.zip")
        self.assertEqual(upload.content_type, "application/zip")

    async def test_rejects_unbounded_reads(self) -> None:
        upload = RequestStreamUpload(
            SimpleNamespace(stream=lambda: chunks(b"private")),
            filename="upload.zip",
            content_type="application/zip",
        )

        with self.assertRaisesRegex(ValueError, "bounded reads"):
            await upload.read()
