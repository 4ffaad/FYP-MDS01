"""Exercise both video adapters with synthetic frames; no patient data or network."""

from pathlib import Path
import tempfile

import cv2
import numpy as np

from backend.app.database.models.video import VideoPrivacyProfile
from backend.app.video_privacy.processor import VideoPrivacyProcessor


def verify() -> None:
    with tempfile.TemporaryDirectory(prefix="mds01-video-check-") as directory:
        root = Path(directory)
        source = root / "synthetic.mp4"
        writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5, (128, 128))
        assert writer.isOpened(), "MP4 encoder unavailable"
        try:
            for _ in range(4):
                writer.write(np.zeros((128, 128, 3), dtype=np.uint8))
        finally:
            writer.release()
        for profile in VideoPrivacyProfile:
            output = root / f"{profile.value}.mp4"
            preview = root / f"{profile.value}.jpg"
            result = VideoPrivacyProcessor().process(source, output, preview, profile)
            assert result.frame_count == 4
            assert result.detected_frames == 0 and not result.usable
            assert output.stat().st_size > 0 and preview.stat().st_size > 0
    print("Both video runtimes passed the synthetic, no-detection smoke check.")


if __name__ == "__main__":
    verify()
