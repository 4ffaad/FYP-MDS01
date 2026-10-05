"""Public security contracts for private storage and opaque identifiers."""

import asyncio
import io
import unittest
from pathlib import Path
import stat
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import UploadFile

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

    def test_nicolet_data_and_head_pair_extracts_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "nicolet.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("nested/recording.data", b"private samples")
                output.writestr("nested/recording.head", b"private header")

            extracted = SessionStorage(root / "sessions").extract_eeg_recordings("SES-TEST", archive)

            self.assertEqual([path.name for path in extracted], ["recording.data"])
            self.assertEqual((root / "sessions" / "SES-TEST" / "extracted" / "recording.head").read_bytes(), b"private header")

    def test_archive_extracts_multiple_legacy_nicolet_e_recordings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "multiple-nicolet-e.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("patient/recording-10.e", b"synthetic ten")
                output.writestr("patient/recording-2.e", b"synthetic two")

            extracted = SessionStorage(root / "sessions").extract_eeg_recordings(
                "SES-TEST", archive
            )

            self.assertEqual(
                [path.name for path in extracted],
                ["recording-2.e", "recording-10.e"],
            )
            self.assertEqual(
                [path.read_bytes() for path in extracted],
                [b"synthetic two", b"synthetic ten"],
            )

    def test_archive_extracts_mixed_eeg_formats_in_one_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "mixed-eeg.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("case/recording-10.edf", b"synthetic edf")
                output.writestr("case/recording-2.e", b"synthetic legacy nicolet")
                output.writestr("case/recording-1.data", b"synthetic nicolet data")
                output.writestr("case/recording-1.head", b"synthetic nicolet header")

            storage = SessionStorage(root / "sessions")
            extracted = storage.extract_eeg_recordings("SES-TEST", archive)

            self.assertEqual(
                [path.name for path in extracted],
                ["recording-1.data", "recording-2.e", "recording-10.edf"],
            )
            self.assertEqual(
                (root / "sessions" / "SES-TEST" / "extracted" / "recording-1.head").read_bytes(),
                b"synthetic nicolet header",
            )

    def test_nicolet_data_without_head_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "incomplete-nicolet.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("recording.data", b"private samples")

            with self.assertRaisesRegex(StorageError, "matching .head"):
                SessionStorage(root / "sessions").extract_eeg_recordings("SES-TEST", archive)

    def test_duplicate_casefolded_nicolet_headers_are_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "ambiguous-nicolet.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("nested/recording.data", b"private samples")
                output.writestr("nested/recording.head", b"first private header")
                output.writestr("NESTED/RECORDING.HEAD", b"second private header")

            storage = SessionStorage(root / "sessions")
            with self.assertRaisesRegex(StorageError, "duplicate archive member"):
                storage.extract_eeg_recordings("SES-TEST", archive)

            self.assertFalse(
                (root / "sessions" / "SES-TEST" / "extracted" / "recording.data").exists()
            )

    def test_unicode_equivalent_edf_basenames_are_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unicode-collisions.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("one/é.edf", b"first synthetic EDF")
                output.writestr("two/e\u0301.edf", b"second synthetic EDF")

            storage = SessionStorage(root / "sessions")
            with self.assertRaisesRegex(StorageError, "duplicate EEG filenames"):
                storage.extract_eeg_recordings("SES-TEST", archive)

            extracted_dir = root / "sessions" / "SES-TEST" / "extracted"
            self.assertEqual(list(extracted_dir.iterdir()), [])

    def test_unicode_equivalent_nicolet_outputs_are_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unicode-nicolet-collisions.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("one/é.data", b"first synthetic signal")
                output.writestr("one/é.head", b"first synthetic header")
                output.writestr("two/e\u0301.data", b"second synthetic signal")
                output.writestr("two/e\u0301.head", b"second synthetic header")

            storage = SessionStorage(root / "sessions")
            with self.assertRaisesRegex(StorageError, "duplicate EEG filenames"):
                storage.extract_eeg_recordings("SES-TEST", archive)

            extracted_dir = root / "sessions" / "SES-TEST" / "extracted"
            self.assertEqual(list(extracted_dir.iterdir()), [])

    def test_legacy_nicolet_e_extracts_without_a_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "legacy-nicolet.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("patient/recording.e", b"private legacy EEG")

            extracted = SessionStorage(root / "sessions").extract_eeg_recordings("SES-TEST", archive)

            self.assertEqual([path.name for path in extracted], ["recording.e"])
            self.assertEqual(extracted[0].read_bytes(), b"private legacy EEG")

    def test_malformed_embedded_events_do_not_abort_sibling_event_reads(self) -> None:
        from backend.app.eeg.legacy_nicolet import NicoletEvent

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "malformed.e"
            valid = root / "valid.e"
            malformed.write_bytes(b"synthetic malformed event source")
            valid.write_bytes(b"synthetic valid event source")
            event = NicoletEvent(1.0, 2.0, "manual_annotation", True)

            def read_events(path: Path):
                if path == malformed:
                    raise ValueError("malformed synthetic event packet")
                return (event,)

            with patch(
                "backend.app.services.storage_service.read_legacy_eeg_events",
                side_effect=read_events,
            ):
                extracted = SessionStorage(root / "sessions").read_embedded_eeg_events(
                    [malformed, valid]
                )

        self.assertEqual(
            extracted,
            {
                "valid.e": [
                    {
                        "onset_seconds": 1.0,
                        "duration_seconds": 2.0,
                        "kind": "manual_annotation",
                        "text_present": True,
                    }
                ]
            },
        )

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
                with patch(
                    "backend.app.services.storage_service.zipfile.ZipFile",
                    side_effect=AssertionError("ZIP constructor ran before the member cap"),
                ) as zip_constructor:
                    storage = SessionStorage(root / "sessions")
                    with self.assertRaisesRegex(StorageError, "too many members"):
                        storage.extract_edfs("SES-TEST", archive)
                    with self.assertRaisesRegex(StorageError, "too many members"):
                        storage.read_reference_annotations(archive)
                    zip_constructor.assert_not_called()

    def test_zip64_archive_member_count_is_bounded_before_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "many-zip64-members.zip"
            with patch("zipfile.ZIP_FILECOUNT_LIMIT", 1):
                with zipfile.ZipFile(archive, "w") as output:
                    output.writestr("recording.edf", b"1")
                    output.writestr("notes.txt", b"2")
            self.assertIn(b"PK\x06\x06", archive.read_bytes())

            with patch("backend.app.services.storage_service.MAX_ARCHIVE_MEMBER_COUNT", 1):
                with patch(
                    "backend.app.services.storage_service.zipfile.ZipFile",
                    side_effect=AssertionError("ZIP64 constructor ran before the member cap"),
                ) as zip_constructor:
                    with self.assertRaisesRegex(StorageError, "too many members"):
                        SessionStorage(root / "sessions").extract_edfs("SES-TEST", archive)
                    zip_constructor.assert_not_called()

    def test_archive_central_directory_size_is_bounded_before_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "large-central-directory.zip"
            with patch("zipfile.ZIP_FILECOUNT_LIMIT", 1):
                with zipfile.ZipFile(archive, "w") as output:
                    output.writestr("recording.edf", b"1")
                    output.writestr("notes.txt", b"2")
            self.assertIn(b"PK\x06\x06", archive.read_bytes())

            with patch(
                "backend.app.services.storage_service._MAX_ARCHIVE_CENTRAL_DIRECTORY_BYTES",
                1,
                create=True,
            ):
                with patch(
                    "backend.app.services.storage_service.zipfile.ZipFile",
                    side_effect=AssertionError("ZIP constructor ran before the directory-size cap"),
                ) as zip_constructor:
                    with self.assertRaisesRegex(StorageError, "central directory exceeds"):
                        SessionStorage(root / "sessions").extract_edfs("SES-TEST", archive)
                    zip_constructor.assert_not_called()

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

    def test_ciphertext_cannot_be_replayed_under_another_session_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", storage_key=b"s" * 32)
            source = asyncio.run(
                storage.save_upload(
                    "SES-SOURCE",
                    UploadFile(filename="source.zip", file=io.BytesIO(b"private source")),
                )
            )
            replay = storage.directory("SES-TARGET", "original") / "upload.zip.enc"
            shutil.copy2(source, replay)

            with self.assertRaises(StorageError):
                storage.materialize_archive("SES-TARGET", replay)

    def test_draft_promotion_reencrypts_for_the_final_session_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", storage_key=b"s" * 32)
            payload = b"private staged archive"
            asyncio.run(
                storage.save_draft_upload(
                    "UPL-DRAFT",
                    UploadFile(filename="source.zip", file=io.BytesIO(payload)),
                )
            )

            promoted = storage.promote_draft("UPL-DRAFT", "SES-FINAL")

            self.assertTrue(promoted.read_bytes().startswith(b"MDS01GCM2"))
            self.assertEqual(storage.materialize_archive("SES-FINAL", promoted).read_bytes(), payload)

    def test_tampered_draft_promotion_leaves_no_partial_session_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions", storage_key=b"s" * 32)
            staged = asyncio.run(
                storage.save_draft_upload(
                    "UPL-TAMPER",
                    UploadFile(filename="source.zip", file=io.BytesIO(b"private archive")),
                )
            )
            with staged.open("r+b") as encrypted:
                encrypted.seek(24)
                byte = encrypted.read(1)
                encrypted.seek(24)
                encrypted.write(bytes([byte[0] ^ 0xFF]))

            with self.assertRaises(StorageError):
                storage.promote_draft("UPL-TAMPER", "SES-TAMPER")

            self.assertTrue(staged.exists())
            self.assertFalse((storage.root / "SES-TAMPER" / "original" / "upload.zip.enc").exists())

    def test_legacy_ciphertext_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key = b"s" * 32
            storage = SessionStorage(Path(directory) / "sessions", storage_key=key)
            payload = b"legacy encrypted archive"
            nonce = b"n" * 12
            legacy = b"MDS01GCM1" + nonce + AESGCM(key).encrypt(nonce, payload, None)
            encrypted = storage.directory("SES-LEGACY", "original") / "upload.zip.enc"
            encrypted.write_bytes(legacy)

            self.assertEqual(storage.materialize_archive("SES-LEGACY", encrypted).read_bytes(), payload)
            self.assertTrue(encrypted.read_bytes().startswith(b"MDS01GCM2"))

    def test_legacy_draft_can_be_promoted_to_a_bound_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key = b"s" * 32
            storage = SessionStorage(Path(directory) / "sessions", storage_key=key)
            payload = b"legacy staged archive"
            nonce = b"n" * 12
            legacy = b"MDS01GCM1" + nonce + AESGCM(key).encrypt(nonce, payload, None)
            staged = storage.draft_path("UPL-LEGACY")
            staged.write_bytes(legacy)

            promoted = storage.promote_draft("UPL-LEGACY", "SES-LEGACY")

            self.assertTrue(promoted.read_bytes().startswith(b"MDS01GCM2"))
            self.assertEqual(storage.materialize_archive("SES-LEGACY", promoted).read_bytes(), payload)

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
