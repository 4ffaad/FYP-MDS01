from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from backend.app.eeg.io import EEGTechnicalMetadata, unsupported_eeg_format_message
from backend.app.services.storage_service import SessionStorage
from backend.app.services.validation_service import validate_eeg


class EEGArchiveDispatchTests(unittest.TestCase):
    def test_unsupported_extension_diagnostic_does_not_echo_filename_suffix(self) -> None:
        message = unsupported_eeg_format_message(Path("/private/recording.Smith"))

        self.assertNotIn("smith", message.lower())
        self.assertNotIn("/private", message)
        self.assertIn("Unsupported EEG format", message)

    def test_legacy_e_extension_survives_archive_extraction_and_validation_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic-eeg.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("case/recording.e", b"synthetic legacy EEG")
            storage = SessionStorage(root / "sessions")
            extracted = storage.extract_eeg_recordings("SES-SYNTHETIC", archive)
            metadata = EEGTechnicalMetadata(
                format="nicolet-e",
                duration_seconds=4.0,
                sampling_rate=256,
                channel_count=18,
                channel_labels=["synthetic-channel"],
            )

            with patch(
                "backend.app.services.validation_service.validate_legacy_nicolet_e",
                return_value=metadata,
            ) as validate_legacy:
                result = validate_eeg(extracted[0])

        self.assertEqual(extracted[0].suffix, ".e")
        self.assertEqual(result["format"], "nicolet-e")
        validate_legacy.assert_called_once_with(extracted[0])


if __name__ == "__main__":
    unittest.main()
