"""Generate a synthetic, patient-free-by-design EDF archive for browser tests."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import tempfile
import zipfile

import numpy as np
import pyedflib

from backend.app.eeg.model_input import MODEL_CHANNELS


def generate_archive(destination: Path) -> None:
    """Write one valid model-compatible EDF containing privacy canaries."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        edf_path = Path(directory) / "CANARY_ORIGINAL_FILENAME.edf"
        sample_count = 4 * 256
        time = np.arange(sample_count, dtype=np.float64) / 256
        samples = np.asarray(
            [120 * np.sin(2 * np.pi * (5 + index / 10) * time) for index in range(len(MODEL_CHANNELS))]
        )
        signal_headers = [
            {
                "label": label,
                "dimension": "uV",
                "sample_frequency": 256,
                "physical_min": -1000,
                "physical_max": 1000,
                "digital_min": -32768,
                "digital_max": 32767,
                "prefilter": "CANARY_PREFILTER",
                "transducer": "CANARY_TRANSDUCER",
            }
            for label in MODEL_CHANNELS
        ]
        writer = pyedflib.EdfWriter(str(edf_path), len(MODEL_CHANNELS), file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            writer.setHeader(
                {
                    "technician": "CANARY_TECHNICIAN",
                    "recording_additional": "CANARY_WARD",
                    "patientname": "CANARY_PATIENT",
                    "patient_additional": "CANARY_ADDRESS",
                    "patientcode": "CANARY_CODE",
                    "equipment": "CANARY_DEVICE",
                    "admincode": "CANARY_ADMIN",
                    "sex": "X",
                    "startdate": datetime(2025, 1, 1),
                    "birthdate": "01 jan 1990",
                }
            )
            writer.setSignalHeaders(signal_headers)
            writer.writeSamples(samples)
            writer.writeAnnotation(1, 1, "CANARY_ANNOTATION")
        finally:
            writer.close()
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(edf_path, edf_path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    generate_archive(parser.parse_args().destination)
