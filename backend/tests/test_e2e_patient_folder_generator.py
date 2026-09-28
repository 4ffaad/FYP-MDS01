"""Synthetic folder fixture for the real patient-intake workflow."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

import pyedflib

from backend.tests import generate_e2e_archive as fixture_generator
from backend.tests.generate_e2e_archive import generate_patient_folder


class GenerateE2EPatientFolderTests(unittest.TestCase):
    def test_synthetic_veeg_fixture_has_no_person_metadata_or_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            patient_folder = Path(directory) / "synthetic-veeg-folder"
            fixture_generator.generate_synthetic_patient_folder(patient_folder)

            self.assertEqual(
                {path.name for path in patient_folder.iterdir()},
                {"synthetic-veeg.edf", "synthetic-report.docx"},
            )
            reader = pyedflib.EdfReader(str(patient_folder / "synthetic-veeg.edf"))
            try:
                header = reader.getHeader()
                self.assertEqual(header["patientname"], "SYNTHETIC TEST DATA")
                self.assertEqual(header["patientcode"], "SYNTHETIC TEST DATA")
                self.assertEqual(header["patient_additional"], "")
                self.assertEqual(header["birthdate"], "")
                self.assertEqual(list(reader.getSampleFrequencies()), [256] * 18)
                self.assertEqual(list(reader.readAnnotations()[2]), [])
            finally:
                reader.close()
            with zipfile.ZipFile(patient_folder / "synthetic-report.docx") as report:
                document = report.read("word/document.xml").decode("utf-8")
            self.assertIn("Technical Summary: SYNTHETIC_VEEG_STUDY", document)
            self.assertNotIn("Patient Name:", document)
            self.assertNotIn("CANARY_", document)

    def test_creates_an_edf_and_local_extractable_docx_without_patient_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            patient_folder = Path(directory) / "synthetic-patient-folder"
            generate_patient_folder(patient_folder)

            self.assertEqual(
                {path.name for path in patient_folder.iterdir()},
                {"CANARY_ORIGINAL_FILENAME.edf", "CANARY_REPORT.docx"},
            )
            reader = pyedflib.EdfReader(
                str(patient_folder / "CANARY_ORIGINAL_FILENAME.edf")
            )
            try:
                self.assertEqual(list(reader.getSampleFrequencies()), [256] * 18)
            finally:
                reader.close()
            with zipfile.ZipFile(patient_folder / "CANARY_REPORT.docx") as report:
                self.assertIn("word/document.xml", report.namelist())
                document = report.read("word/document.xml").decode("utf-8")
            self.assertIn("Patient Name: CANARY_PATIENT", document)
            self.assertIn("Technical Summary: Synthetic test report", document)

    def test_refuses_to_overwrite_an_existing_fixture_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            patient_folder = Path(directory) / "existing"
            patient_folder.mkdir()
            sentinel = patient_folder / "keep.txt"
            sentinel.write_text("leave intact", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                generate_patient_folder(patient_folder)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "leave intact")
