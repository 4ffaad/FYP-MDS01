"""Basic end-to-end checks using a small synthetic EDF fixture.

Run with: .venv/bin/python -m unittest discover -s tests -v
"""

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pyedflib

from backend.app.privacy.deidentify import deidentify_edf, generate_record_id, inspect_metadata
from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.preprocessing import EEGPreprocessor
from backend.app.eeg.model_input import MODEL_CHANNELS, prepare_model_windows
from backend.app.ml.stub_inference import StubInferenceService
from backend.app.services.storage_service import SessionStorage, StorageError


class BackendTests(unittest.TestCase):
    def _create_source_edf(self, path: Path) -> np.ndarray:
        samples = np.array([
            np.arange(512, dtype=np.int32) - 256,
            np.arange(512, dtype=np.int32) - 128,
        ])
        headers = [
            {
                "label": label,
                "dimension": "uV",
                "sample_frequency": 256,
                "physical_min": -1000,
                "physical_max": 1000,
                "digital_min": -2048,
                "digital_max": 2047,
                "prefilter": "",
                "transducer": "",
            }
            for label in ("FP1-F7", "F7-T7")
        ]
        writer = pyedflib.EdfWriter(str(path), 2, file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            writer.setHeader({
                "technician": "Technician Name",
                "recording_additional": "Ward 2",
                "patientname": "Jane Doe",
                "patient_additional": "Address",
                "patientcode": "PATIENT-123",
                "equipment": "EEG Device",
                "admincode": "ADMIN-1",
                "sex": "F",
                "startdate": datetime(2025, 1, 1, 12, 0, 0),
                "birthdate": "01 jan 1990",
            })
            writer.setSignalHeaders(headers)
            writer.writeSamples(samples, digital=True)
        finally:
            writer.close()
        return samples

    def test_deidentification_preserves_eeg_and_sanitizes_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.edf", root / "anonymous.edf"
            original = self._create_source_edf(source)
            anonymous_id = generate_record_id()
            deidentify_edf(source, output, anonymous_id)

            self.assertTrue(output.exists())
            reader = pyedflib.EdfReader(str(output))
            try:
                copied = np.asarray([reader.readSignal(i, digital=True) for i in range(2)])
                self.assertTrue(np.array_equal(copied, original))
                self.assertEqual(reader.getSignalLabels(), ["FP1-F7", "F7-T7"])
                self.assertEqual(reader.getSampleFrequencies().tolist(), [256.0, 256.0])
                self.assertEqual(reader.getPatientName(), anonymous_id)
                self.assertEqual(reader.getPatientCode(), anonymous_id)
                self.assertEqual(reader.getTechnician(), "")
                self.assertEqual(reader.getBirthdate(), "")
            finally:
                reader.close()

            metadata = inspect_metadata(output)
            self.assertEqual(metadata["technical"]["number_of_channels"], 2)
            self.assertFalse(any(metadata["potential_identifiers_present"].values()))

    def test_preprocessing_preserves_shape_and_clips_values(self) -> None:
        data = np.vstack((np.sin(np.linspace(0, 20, 512)), np.zeros(512)))
        processed = EEGPreprocessor(sampling_rate=256).preprocess(data)
        self.assertEqual(processed.shape, data.shape)
        self.assertLessEqual(np.abs(processed).max(), 5)

    def test_model_windows_match_the_trained_input_contract(self) -> None:
        labels = list(MODEL_CHANNELS) + ["P7-T7", "T7-FT9", "FT9-FT10", "FT10-T8", "T8-P8"]
        signals = np.arange(23 * 2048, dtype=np.float64).reshape(23, 2048)
        windows, starts, discarded = prepare_model_windows(signals, 256, labels)

        self.assertEqual(windows.shape, (2, 1024, 18))
        self.assertEqual(windows.dtype, np.float32)
        self.assertEqual(starts.tolist(), [0.0, 4.0])
        self.assertEqual(discarded, 0)
        self.assertEqual(windows[0, 0, 0], signals[0, 0])
        self.assertEqual(windows[1, 0, 17], signals[17, 1024])

    def test_uniform_reader_reopens_edf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.edf"
            self._create_source_edf(source)
            data, frequency, labels = read_uniform_edf(source)
            self.assertEqual(data.shape, (2, 512))
            self.assertEqual(frequency, 256)
            self.assertEqual(labels, ["FP1-F7", "F7-T7"])

    def test_stub_predictions_are_deterministic_and_non_clinical_contract_is_stable(self) -> None:
        service = StubInferenceService()
        windows = np.zeros((2, 1024, 18), dtype=np.float32)
        starts = np.asarray([0.0, 4.0], dtype=np.float32)
        first = service.predict(windows, starts, "REC-TEST")
        second = service.predict(windows, starts, "REC-TEST")
        self.assertEqual(first, second)
        self.assertEqual(service.model_name, "development-stub")
        self.assertEqual(service.model_version, "stub-0.1.0")
        self.assertTrue(all(0 <= item.probability <= 1 for item in first))

    def test_storage_rejects_archive_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = SessionStorage(Path(directory) / "sessions")
            archive = Path(directory) / "unsafe.zip"
            import zipfile

            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.edf", b"not an EDF")
            with self.assertRaises(StorageError):
                storage.extract_edfs("SES-TEST", archive)

if __name__ == "__main__":
    unittest.main()
