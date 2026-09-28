"""Basic PDF envelope checks reject obviously truncated uploads."""

import unittest

from backend.app.services.case_source_report_service import InvalidCaseSourceReport, _validate_pdf


class CaseSourceReportPdfValidationTests(unittest.TestCase):
    def test_accepts_pdf_header_and_end_marker(self) -> None:
        _validate_pdf(b"%PDF-1.7\nsynthetic object data\n%%EOF\n")

    def test_rejects_header_without_end_marker(self) -> None:
        with self.assertRaises(InvalidCaseSourceReport):
            _validate_pdf(b"%PDF-1.7\nsynthetic truncated object data")


if __name__ == "__main__":
    unittest.main()
