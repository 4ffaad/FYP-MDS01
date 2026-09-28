"""Explicit OpenAPI contracts for streamed private-media uploads."""

import unittest

from backend.app.main import app


class StreamedUploadOpenAPITests(unittest.TestCase):
    def test_raw_binary_routes_advertise_their_request_media_type(self) -> None:
        schema = app.openapi()
        paths = {
            "/api/sessions/upload": "post",
            "/api/uploads/drafts": "post",
            "/api/video-privacy/jobs": "post",
            "/api/video-detection/jobs": "post",
            "/api/video-detection/preflight": "post",
        }
        for path, method in paths.items():
            with self.subTest(path=path):
                request_body = schema["paths"][path][method]["requestBody"]
                self.assertIn("application/octet-stream", request_body["content"])
                self.assertEqual(
                    request_body["content"]["application/octet-stream"]["schema"],
                    {"type": "string", "format": "binary"},
                )

    def test_source_report_upload_advertises_pdf_body(self) -> None:
        schema = app.openapi()
        request_body = schema["paths"]["/api/cases/{case_id}/report"]["put"]["requestBody"]
        self.assertEqual(
            request_body["content"]["application/pdf"]["schema"],
            {"type": "string", "format": "binary"},
        )

    def test_detection_visualization_is_not_a_public_route(self) -> None:
        schema = app.openapi()
        self.assertNotIn("/api/video-detection/jobs/{job_id}/visualization", schema["paths"])


if __name__ == "__main__":
    unittest.main()
