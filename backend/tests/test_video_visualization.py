"""Synthetic contract tests for the privacy-safe detection visualization."""

from importlib import import_module
import json
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
    _pose_at_time,
    _redact_face,
    render_visualization,
    validate_visualization_artifact,
)
from backend.app.video_detection.contract import DetectionError


def patient_pose(width: int = 200, height: int = 200) -> np.ndarray:
    pose = np.zeros((18, 3), dtype=np.float32)
    points = {
        0: (0.50, 0.18), 14: (0.47, 0.19), 15: (0.53, 0.19),
        16: (0.42, 0.19), 17: (0.58, 0.19),
        2: (0.43, 0.35), 3: (0.34, 0.44), 4: (0.27, 0.52),
        5: (0.57, 0.35), 6: (0.66, 0.44), 7: (0.73, 0.52),
        8: (0.44, 0.56), 9: (0.40, 0.72), 10: (0.37, 0.84),
        11: (0.56, 0.56), 12: (0.60, 0.72), 13: (0.64, 0.84),
    }
    for index, (x, y) in points.items():
        pose[index] = (x * width, y * height, 1.0)
    return pose


class VideoVisualizationTests(unittest.TestCase):
    def test_interpolates_patient_pose_between_output_frames(self):
        first = patient_pose()
        second = first.copy()
        second[:, 0] += 20

        interpolated = _pose_at_time(
            [(0.0, first), (0.2, second)], [0.0, 0.2], 0.1
        )

        self.assertIsNotNone(interpolated)
        required = [0, 14, 15, *range(2, 14)]
        self.assertTrue(
            np.allclose(interpolated[required, 0], first[required, 0] + 10)
        )
        self.assertIsNone(
            _pose_at_time([(0.0, first), (0.5, second)], [0.0, 0.5], 0.25)
        )
        self.assertIsNotNone(
            _pose_at_time([(0.0, first)], [0.0], 1 / 6 + 5e-7)
        )
        self.assertIsNone(_pose_at_time([(0.0, first)], [0.0], 1 / 6 + 2e-6))

    def test_blurs_the_face_without_blurring_the_rest_of_the_patient(self):
        class FakeCV2:
            @staticmethod
            def GaussianBlur(region, *_args, **_kwargs):
                return np.zeros_like(region)

        source = np.full((200, 200, 3), 120, dtype=np.uint8)
        protected, face_blurred = _redact_face(
            FakeCV2, source, patient_pose()
        )

        self.assertTrue(face_blurred)
        self.assertTrue(np.all(protected[38, 100] == 0))
        self.assertTrue(np.all(protected[70, 100] == 0))
        self.assertTrue(np.all(protected[100, 100] == source[100, 100]))
        self.assertTrue(np.all(protected[0, 0] == source[0, 0]))

    def test_missing_face_landmarks_fall_back_to_full_frame(self):
        class FakeCV2:
            @staticmethod
            def GaussianBlur(frame, *_args, **_kwargs):
                return np.zeros_like(frame)

        source = np.full((64, 96, 3), 120, dtype=np.uint8)
        protected, face_blurred = _redact_face(FakeCV2, source, None)

        self.assertFalse(face_blurred)
        self.assertTrue(np.all(protected == 0))

    def test_full_frame_blur_is_the_fallback_when_patient_pose_is_missing(self):
        class FakeCV2:
            @staticmethod
            def GaussianBlur(frame, *_args, **_kwargs):
                FakeCV2.blurred_shape = frame.shape
                return blurred

            blurred_shape = None

        source = np.full((64, 96, 3), 120, dtype=np.uint8)
        blurred = np.full_like(source, 25)
        protected, face_blurred = _redact_face(FakeCV2, source, None)

        self.assertFalse(face_blurred)
        self.assertEqual(FakeCV2.blurred_shape, source.shape)
        self.assertTrue(np.all(protected == blurred))

    def test_render_blurs_face_and_writes_video_only_preview(self):
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
                (320, 240),
            )
            self.assertTrue(writer.isOpened())
            for frame_index in range(2):
                frame = np.full((240, 320, 3), 24, dtype=np.uint8)
                for y in range(24, 216, 4):
                    for x in range(64, 257, 4):
                        frame[y : y + 2, x : x + 2] = (
                            20 + x % 200,
                            40 + y % 200,
                            180,
                        )
                writer.write(frame)
            writer.release()

            keypoints = patient_pose(width=320, height=240)
            metadata = render_visualization(source, output, [(0.0, keypoints)])

            self.assertTrue(metadata["available"])
            self.assertFalse(metadata["audio_included"])
            self.assertEqual(
                metadata["privacy_method"],
                "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
            )
            self.assertEqual(metadata["face_blur_coverage"], 1.0)
            self.assertEqual(metadata["full_frame_fallback_frames"], 0)
            self.assertTrue(metadata["overlay"]["skeleton"])
            capture = cv2.VideoCapture(str(output))
            self.assertTrue(capture.isOpened())
            success, rendered = capture.read()
            capture.release()
            self.assertTrue(success)
            self.assertEqual(rendered.shape[:2], (240, 320))
            self.assertEqual(metadata["face_blur_coverage"], 1.0)
            validate_visualization_artifact(output)

    def test_render_blurred_preview_without_pose_detections(self):
        if not all(hasattr(cv2, name) for name in ("VideoWriter", "VideoCapture", "VideoWriter_fourcc")):
            self.skipTest("local cv2 environment has no video codec support")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "synthetic-source.mp4"
            output = root / "protected.mp4"
            preview = root / "protected-preview.jpg"
            writer = cv2.VideoWriter(
                str(source), cv2.VideoWriter_fourcc(*"mp4v"), 6.0, (96, 64)
            )
            self.assertTrue(writer.isOpened())
            writer.write(np.full((64, 96, 3), 120, dtype=np.uint8))
            writer.release()

            metadata = render_visualization(source, output, [], preview_path=preview)

            self.assertTrue(metadata["available"])
            self.assertFalse(metadata["pose_overlay_available"])
            self.assertEqual(metadata["full_frame_fallback_frames"], 1)
            self.assertEqual(metadata["pose_sample_count"], 0)
            self.assertTrue(preview.is_file())
            self.assertGreater(preview.stat().st_size, 0)
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

    def test_validator_rejects_browser_unsupported_video_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "review.mp4"
            artifact.write_bytes(b"fixture")
            for codec, pixel_format in (("mpeg4", "yuv420p"), ("h264", "yuv444p")):
                probe = subprocess.CompletedProcess(
                    ["ffprobe"],
                    0,
                    stdout=json.dumps(
                        {
                            "streams": [
                                {
                                    "codec_type": "video",
                                    "codec_name": codec,
                                    "pix_fmt": pixel_format,
                                }
                            ],
                            "format": {"duration": "1"},
                        }
                    ),
                    stderr="",
                )
                with self.subTest(codec=codec, pixel_format=pixel_format):
                    with patch(
                        "backend.app.video_detection.visualization.shutil.which",
                        return_value="/usr/bin/ffprobe",
                    ), patch(
                        "backend.app.video_detection.visualization.subprocess.run",
                        return_value=probe,
                    ), self.assertRaisesRegex(DetectionError, "visualization_failed"):
                        validate_visualization_artifact(artifact)


if __name__ == "__main__":
    unittest.main()
