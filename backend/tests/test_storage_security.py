"""Public security contracts for private storage and opaque identifiers."""

import unittest
from pathlib import Path
import stat
import tempfile
import zipfile
from unittest.mock import patch

from backend.app.privacy.deidentify import generate_record_id
from backend.app.services.session_service import new_draft_id, new_session_id
from backend.app.services.storage_service import SessionStorage, StorageError


class StorageSecurityTests(unittest.TestCase):
    """Verify externally observable storage hardening behavior."""

    def test_public_identifiers_contain_at_least_128_random_bits(self) -> None:
        """Session, recording, and draft IDs retain prefixes and 128-bit tokens."""

        for prefix, identifier in (
            ("SES-", new_session_id()),
            ("REC-", generate_record_id()),
            ("UPL-", new_draft_id()),
        ):
            token = identifier.removeprefix(prefix)
            self.assertTrue(identifier.startswith(prefix))
            self.assertGreaterEqual(len(token), 32)
            self.assertEqual(int(token, 16).bit_length() <= len(token) * 4, True)

    def test_private_directories_and_extracted_files_are_owner_only(self) -> None:
        """New session storage uses 0700 directories and 0600 private files."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            storage = SessionStorage(root)
            session_dir = storage.session_dir("SES-TEST")
            draft_dir = storage.draft_dir("UPL-TEST")
            archive = Path(directory) / "recordings.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("recording.edf", b"private EEG")

            extracted = storage.extract_edfs("SES-TEST", archive)

            for path in (session_dir, draft_dir, session_dir / "extracted"):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(extracted[0].stat().st_mode), 0o600)

    def test_archive_exceeding_cumulative_uncompressed_limit_is_rejected(self) -> None:
        """An archive cannot bypass limits with many individually small EDFs."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "too-large.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("recording_01.edf", b"123456")
                output.writestr("recording_02.edf", b"123456")

            with patch("backend.app.services.storage_service.MAX_ARCHIVE_TOTAL_BYTES", 10):
                with self.assertRaisesRegex(StorageError, "total size limit"):
                    SessionStorage(root / "sessions").extract_edfs("SES-TEST", archive)

    def test_archive_with_extreme_compression_ratio_is_rejected(self) -> None:
        """Highly compressed EDF members are rejected before extraction."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "compression-bomb.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
                output.writestr("recording.edf", b"0" * 10_000)

            with patch("backend.app.services.storage_service.MAX_ZIP_COMPRESSION_RATIO", 10):
                with self.assertRaisesRegex(StorageError, "compression ratio"):
                    SessionStorage(root / "sessions").extract_edfs("SES-TEST", archive)


if __name__ == "__main__":
    unittest.main()
