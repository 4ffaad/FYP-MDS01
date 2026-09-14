"""Manifest generation checks without touching patient data."""

from pathlib import Path
import unittest

from backend.scripts.create_video_evaluation_manifest import split_by_subject, subject_id


class VideoEvaluationManifestTests(unittest.TestCase):
    def test_subjects_are_stable_and_disjoint(self):
        splits = split_by_subject({"S1", "S2", "S3", "S4", "S5"}, 7)
        self.assertEqual(set(splits), {"S1", "S2", "S3", "S4", "S5"})
        self.assertEqual(set(splits.values()), {"train", "calibration", "test"})
        self.assertEqual(subject_id(Path("S47_11_74.mp4")), "S47")


if __name__ == "__main__":
    unittest.main()
