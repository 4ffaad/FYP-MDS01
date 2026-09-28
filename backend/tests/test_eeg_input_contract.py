"""Regression tests for fail-closed EEG sampling/timeline validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest
import warnings

import numpy as np
import pyedflib

from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.io import read_uniform_nicolet
from backend.app.services.validation_service import ValidationError, validate_eeg, validate_edf


class EEGInputContractTests(unittest.TestCase):
    """Reject inputs the fixed model contract cannot represent safely."""

    @staticmethod
    def _write_edf(path: Path, *, sample_frequency: float, record_duration: float, sample_count: int) -> None:
        writer = pyedflib.EdfWriter(str(path), 1, file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            writer.setHeader(  # type: ignore[arg-type]
                {
                    "technician": "",
                    "recording_additional": "",
                    "patientname": "",
                    "patient_additional": "",
                    "patientcode": "",
                    "equipment": "synthetic",
                    "admincode": "",
                    "sex": "X",
                    "startdate": datetime(2024, 1, 1),
                    "birthdate": "",
                }
            )
            writer.setSignalHeaders(
                [
                    {
                        "label": "FP1-F7",
                        "dimension": "uV",
                        "sample_frequency": sample_frequency,
                        "physical_min": -1,
                        "physical_max": 1,
                        "digital_min": -32768,
                        "digital_max": 32767,
                        "transducer": "",
                        "prefilter": "",
                    }
                ]
            )
            if record_duration != 1.0:
                writer.setDatarecordDuration(record_duration)
            writer.writeSamples([np.zeros(sample_count, dtype=np.float64)])
        finally:
            writer.close()

    @staticmethod
    def _write_nicolet_data(path: Path, *, sample_frequency: int) -> None:
        header = "\n".join(
            [
                "elec_names=[FP1-F7,F7-T7]",
                f"sample_freq={sample_frequency}",
                "num_channels=2",
                "num_samples=1024",
                "conversion_factor=1",
                "start_ts=2020-01-01 00:00:00.000",
                "rec_id=1",
                "adm_id=2",
                "pat_id=3",
            ]
        ) + "\n"
        path.with_suffix(".head").write_text(header, encoding="utf-8")
        path.write_bytes(np.zeros((1024, 2), dtype="<i2").tobytes())

    def test_fractional_edf_rate_is_rejected_by_validation_and_reader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fractional.edf"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self._write_edf(
                    source,
                    sample_frequency=256.5,
                    record_duration=2.0,
                    sample_count=513,
                )

            with self.assertRaisesRegex(ValidationError, "256 Hz"):
                validate_edf(source)
            with self.assertRaisesRegex(ValueError, "256 Hz"):
                read_uniform_edf(source)

    def test_discontinuous_edf_plus_is_rejected_before_flattening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "discontinuous.edf"
            self._write_edf(
                source,
                sample_frequency=256,
                record_duration=1.0,
                sample_count=256,
            )
            with source.open("r+b") as recording:
                recording.seek(192)
                recording.write(b"EDF+D")

            with self.assertRaisesRegex(ValidationError, "(?i)discontinuous"):
                validate_edf(source)
            with self.assertRaisesRegex(ValueError, "(?i)discontinuous"):
                read_uniform_edf(source)

    def test_nicolet_data_rate_other_than_256_is_rejected_at_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "unsupported_rate.data"
            self._write_nicolet_data(source, sample_frequency=250)

            with self.assertRaises(ValidationError):
                validate_eeg(source)
            with self.assertRaisesRegex(ValueError, "256 Hz"):
                read_uniform_nicolet(source)

    def test_unsupported_extension_is_reported_without_exposing_the_path(self) -> None:
        source = Path("/private/patient-folder/recording.eeg")

        with self.assertRaisesRegex(ValidationError, r"extension '\.eeg'") as error:
            validate_eeg(source)

        self.assertNotIn(str(source), str(error.exception))


if __name__ == "__main__":
    unittest.main()
