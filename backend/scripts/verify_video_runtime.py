"""Exercise the supported privacy adapter with synthetic frames; no patient data or network."""

from pathlib import Path
import tempfile

import cv2
import numpy as np

from backend.app.database.models.video import VideoPrivacyProfile
from backend.app.video_privacy.processor import VideoPrivacyProcessor
from backend.app.video_detection.visualization import (
    render_visualization,
    validate_visualization_artifact,
)


def require(condition: bool, message: str) -> None:
    """Raise even when Python runs with optimization enabled."""

    if not condition:
        raise RuntimeError(message)


def verify() -> None:
    with tempfile.TemporaryDirectory(prefix="mds01-video-check-") as directory:
        root = Path(directory)
        source = root / "synthetic.mp4"
        writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 6, (128, 128))
        require(writer.isOpened(), "MP4 encoder unavailable")
        try:
            for _ in range(4):
                writer.write(np.zeros((128, 128, 3), dtype=np.uint8))
        finally:
            writer.release()
        profile = VideoPrivacyProfile.FACE_REDACTED
        output = root / f"{profile.value}.mp4"
        preview = root / f"{profile.value}.jpg"
        result = VideoPrivacyProcessor().process(source, output, preview, profile)
        require(result.frame_count == 4, "unexpected synthetic frame count")
        require(result.detected_frames == 0 and not result.usable, "unexpected detection in synthetic input")
        require(output.stat().st_size > 0 and preview.stat().st_size > 0, "privacy output was not created")
        review = root / "review.mp4"
        metadata = render_visualization(source, review, [])
        require(metadata["available"], "synthetic review video was not created")
        require(metadata["full_frame_fallback_frames"] == 4, "unexpected synthetic face fallback")
        validate_visualization_artifact(
            review,
            expected_fps=6,
            expected_width=128,
            expected_height=128,
            expected_frame_count=4,
            expected_duration=4 / 6,
        )
    print("Face-redaction runtime passed the synthetic, no-detection smoke check.")


if __name__ == "__main__":
    verify()
