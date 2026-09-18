"""Synthetic contract tests for the privacy-safe detection visualization."""

from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

import numpy as np

cv2: Any = import_module("cv2")

from backend.app.video_detection.visualization import (
    render_visualization,
    validate_visualization_artifact,
)
from backend.app.video_detection.contract import DetectionError


class VideoVisualizationTests(unittest.TestCase):
    def test_render_masks_pose_region_and_writes_video_only_preview(self):
        if not all(hasattr(cv2, name) for name in ("VideoWriter", "VideoCapture", "VideoWriter_fourcc")):
            self.skipTest("local cv2 environment has no video codec support")
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe is unavailable in the local environment")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            output = root / "protected.mp4"
            writer = cv2.VideoWriter(
                str(source),
                cv2.VideoWriter_fourcc(*"mp4v"),
                6.0,
                (96, 64),
            )
            self.assertTrue(writer.isOpened())
            for frame_index in range(2):
                frame = np.full((64, 96, 3), 24, dtype=np.uint8)
                for y in range(8, 57, 4):
                    for x in range(25, 72, 4):
                        frame[y : y + 2, x : x + 2] = (20 + x, 40 + y, 180)
                writer.write(frame)
            writer.release()

            keypoints = np.zeros((18, 3), dtype=np.float32)
            keypoints[:, 2] = 1.0
            keypoints[:, 0] = np.linspace(42, 54, 18)
            keypoints[:, 1] = np.linspace(10, 54, 18)
            metadata = render_visualization(source, output, [(0.0, keypoints)])

            self.assertTrue(metadata["available"])
            self.assertFalse(metadata["audio_included"])
            self.assertTrue(metadata["overlay"]["skeleton"])
            capture = cv2.VideoCapture(str(output))
            self.assertTrue(capture.isOpened())
            success, rendered = capture.read()
            capture.release()
            self.assertTrue(success)
            self.assertEqual(rendered.shape[:2], (64, 96))
            self.assertFalse(np.array_equal(rendered[12:55, 28:70], np.full((43, 42, 3), 24, dtype=np.uint8)))
            validate_visualization_artifact(output)

    def test_validator_rejects_audio_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "protected.mp4"
            artifact.write_bytes(b"fixture")
            probe = subprocess.CompletedProcess(
                ["ffprobe"],
                0,
                stdout='{"streams":[{"codec_type":"video"},{"codec_type":"audio"}],"format":{"duration":"1"}}',
                stderr="",
            )
            with patch("backend.app.video_detection.visualization.shutil.which", return_value="/usr/bin/ffprobe"), patch(
                "backend.app.video_detection.visualization.subprocess.run", return_value=probe,
            ):
                with self.assertRaisesRegex(DetectionError, "visualization_failed"):
                    validate_visualization_artifact(artifact)


if __name__ == "__main__":
    unittest.main()
