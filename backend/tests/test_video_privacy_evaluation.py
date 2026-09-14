"""Aggregate video privacy utility evaluation checks."""

import json
from pathlib import Path
import tempfile
import unittest

from backend.app.research.video_privacy_evaluation import evaluate_video_privacy, load_manifest, window_labels
from backend.app.video_privacy.processor import VideoProcessingResult


class VideoPrivacyEvaluationTests(unittest.TestCase):
    def test_manifest_is_patient_disjoint_and_report_is_aggregate_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "clip.mp4").write_bytes(b"synthetic")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps([{
                "video": "clip.mp4", "subject_id": "patient-a", "split": "test", "seizure_intervals": [[1, 3]],
            }]))

            class Processor:
                def process(self, *_args):
                    return VideoProcessingResult(4, 30, 10, 10, 120, 120, [], True)

            calls = []
            def runtime(_path):
                calls.append(_path)
                return {"model": {"threshold": 0.5}, "predictions": [
                    {"start_time": 0, "end_time": 2, "score": 0.7},
                    {"start_time": 2, "end_time": 4, "score": 0.2},
                ]}

            report = evaluate_video_privacy(root, manifest, runtime=runtime, processor=Processor())

        self.assertEqual(len(calls), 2)
        self.assertEqual(report["privacy_method"], "face-redaction")
        self.assertEqual(report["subject_count"], 1)
        self.assertNotIn("patient-a", json.dumps(report))
        self.assertEqual(report["threshold_agreement"], 1.0)

    def test_manifest_rejects_subjects_in_multiple_splits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.mp4").write_bytes(b"a")
            (root / "b.mp4").write_bytes(b"b")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps([
                {"video": "a.mp4", "subject_id": "patient-a", "split": "train", "seizure_intervals": []},
                {"video": "b.mp4", "subject_id": "patient-a", "split": "test", "seizure_intervals": []},
            ]))
            with self.assertRaisesRegex(ValueError, "must not span splits"):
                load_manifest(manifest, root, "test")

    def test_window_labels_use_interval_overlap(self):
        labels = window_labels(
            [{"start_time": 0, "end_time": 2}, {"start_time": 2, "end_time": 4}], [[1, 3]],
        )
        self.assertEqual(labels, [1, 1])


if __name__ == "__main__":
    unittest.main()
