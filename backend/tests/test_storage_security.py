"""Public security contracts for private storage and opaque identifiers."""

import asyncio
import unittest
from pathlib import Path
import stat
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from backend.app.privacy.deidentify import generate_record_id
from backend.app.services.session_service import new_draft_id, new_session_id
from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.video_storage_service import CleanupFileResponse, VideoStorage


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

    def test_runtime_directories_are_owner_only_even_with_permissive_umask(self) -> None:
        from backend.app.core import config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session_root = root / "sessions"
            database_root = root / "database"
            with patch.object(config, "SESSION_STORAGE_DIR", session_root), patch.object(
                config, "DATABASE_DIR", database_root
            ), patch("backend.app.core.config.os.umask", return_value=0o022):
                config.ensure_runtime_directories()

            self.assertEqual(stat.S_IMODE(session_root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(database_root.stat().st_mode), 0o700)

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

    def test_session_directory_identifiers_cannot_escape_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions")
            for identifier in ("../outside", "SES-../outside", "not-a-session"):
                with self.subTest(identifier=identifier), self.assertRaises(StorageError):
                    storage.session_dir(identifier)

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

    def test_archive_limit_counts_non_edf_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "metadata-bomb.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("recording.edf", b"1")
                output.writestr("notes.txt", b"123456")

            with patch("backend.app.services.storage_service.MAX_ARCHIVE_TOTAL_BYTES", 5):
                with self.assertRaisesRegex(StorageError, "total size limit"):
                    SessionStorage(root / "sessions").extract_edfs("SES-TEST", archive)

    def test_archive_member_count_is_bounded_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "many-members.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("recording.edf", b"1")
                output.writestr("notes.txt", b"2")

            with patch("backend.app.services.storage_service.MAX_ARCHIVE_MEMBER_COUNT", 1):
                with self.assertRaisesRegex(StorageError, "too many members"):
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

    def test_video_materialization_rejects_outside_root_and_symlink_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            storage = SessionStorage(root, storage_key=b"s" * 32)
            source = Path(directory) / "source.bin"
            source.write_bytes(b"protected")
            retained = storage.store_encrypted_artifact("VID-SAFE", source, "video.visualization.mp4")
            outside = Path(directory) / "outside.enc"
            shutil.copy2(retained, outside)
            with self.assertRaises(StorageError):
                storage.materialize_retained_artifact("VID-SAFE", outside, "preview.mp4")
            symlink = root / "VID-SAFE" / "retained" / "linked.enc"
            symlink.symlink_to(retained)
            with self.assertRaises(StorageError):
                storage.materialize_retained_artifact("VID-SAFE", symlink, "preview.mp4")

    def test_video_visualization_path_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            path = VideoStorage(root).visualization_path("VID-MISSING")
            self.assertEqual(path, root / "VID-MISSING" / "retained" / "video.visualization.mp4.enc")
            self.assertFalse(root.exists())

    def test_cleanup_response_runs_when_stream_send_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protected.mp4"
            path.write_bytes(b"protected")
            cleanup_calls: list[bool] = []

            async def receive():
                return {"type": "http.request"}

            async def send(_message):
                raise RuntimeError("client disconnected")

            response = CleanupFileResponse(
                path,
                cleanup=lambda: cleanup_calls.append(True),
                media_type="video/mp4",
            )
            with self.assertRaisesRegex(RuntimeError, "client disconnected"):
                asyncio.run(response({"type": "http", "method": "GET", "path": "/", "headers": []}, receive, send))
            self.assertEqual(cleanup_calls, [True])


if __name__ == "__main__":
    unittest.main()
