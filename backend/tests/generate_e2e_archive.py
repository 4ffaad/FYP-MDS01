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


def _write_synthetic_edf(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_count = 4 * 256
    time = np.arange(sample_count, dtype=np.float64) / 256
    samples = np.asarray(
        [
            120 * np.sin(2 * np.pi * (5 + index / 10) * time)
            for index in range(len(MODEL_CHANNELS))
        ]
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
    writer = pyedflib.EdfWriter(
        str(destination), len(MODEL_CHANNELS), file_type=pyedflib.FILETYPE_EDFPLUS
    )
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


def generate_archive(destination: Path) -> None:
    """Write one valid model-compatible EDF archive containing privacy canaries."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        edf_path = Path(directory) / "CANARY_ORIGINAL_FILENAME.edf"
        _write_synthetic_edf(edf_path)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(edf_path, edf_path.name)


def generate_patient_folder(destination: Path) -> None:
    """Write an EDF and minimal DOCX fixture for the current folder intake UI."""
    destination.mkdir(parents=True, exist_ok=False)
    _write_synthetic_edf(destination / "CANARY_ORIGINAL_FILENAME.edf")
    with zipfile.ZipFile(
        destination / "CANARY_REPORT.docx", "w", compression=zipfile.ZIP_DEFLATED
    ) as report:
        report.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        report.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        report.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Patient Name: CANARY_PATIENT</w:t></w:r></w:p>
    <w:p><w:r><w:t>Technical Summary: Synthetic test report</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>""",
        )


def _write_synthetic_veeg_edf(destination: Path) -> None:
    """Write one model-contract EDF with synthetic identifiers and no annotations."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_count = 4 * 256
    time = np.arange(sample_count, dtype=np.float64) / 256
    samples = np.asarray(
        [
            120 * np.sin(2 * np.pi * (5 + index / 10) * time)
            for index in range(len(MODEL_CHANNELS))
        ]
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
            "prefilter": "",
            "transducer": "",
        }
        for label in MODEL_CHANNELS
    ]
    writer = pyedflib.EdfWriter(
        str(destination), len(MODEL_CHANNELS), file_type=pyedflib.FILETYPE_EDFPLUS
    )
    try:
        writer.setHeader(
            {
                "technician": "SYNTHETIC_TEST_DATA",
                "recording_additional": "SYNTHETIC_TEST_DATA",
                "patientname": "SYNTHETIC_TEST_DATA",
                "patient_additional": "",
                "patientcode": "SYNTHETIC_TEST_DATA",
                "equipment": "SYNTHETIC_TEST_DATA",
                "admincode": "",
                "sex": "",
                "startdate": datetime(2000, 1, 1),
                "birthdate": "",
            }
        )
        writer.setSignalHeaders(signal_headers)
        writer.writeSamples(samples)
    finally:
        writer.close()


def generate_synthetic_patient_folder(destination: Path) -> None:
    """Write a macOS-extractable report and VEEG file with no person metadata."""
    destination.mkdir(parents=True, exist_ok=False)
    _write_synthetic_veeg_edf(destination / "synthetic-veeg.edf")
    with zipfile.ZipFile(
        destination / "synthetic-report.docx", "w", compression=zipfile.ZIP_DEFLATED
    ) as report:
        report.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        report.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        report.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Technical Summary: SYNTHETIC_VEEG_STUDY</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>""",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--patient-folder", action="store_true")
    parser.add_argument("--synthetic-veeg-folder", action="store_true")
    arguments = parser.parse_args()
    if arguments.patient_folder and arguments.synthetic_veeg_folder:
        parser.error("Choose only one patient-folder mode.")
    if arguments.synthetic_veeg_folder:
        generate_synthetic_patient_folder(arguments.destination)
    elif arguments.patient_folder:
        generate_patient_folder(arguments.destination)
    else:
        generate_archive(arguments.destination)
