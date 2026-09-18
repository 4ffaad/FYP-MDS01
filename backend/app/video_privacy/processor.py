"""Fail-closed OpenCV adapter for the privacy-only video transform."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import math
from pathlib import Path
import time
from typing import Any

import numpy as np

from backend.app.core.config import (
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_MAX_FPS,
    VIDEO_MAX_FRAMES,
    VIDEO_MAX_HEIGHT,
    VIDEO_MAX_OUTPUT_BYTES,
    VIDEO_MAX_WIDTH,
    VIDEO_MIN_FPS,
    VIDEO_PRIVACY_TIMEOUT_SECONDS,
)
from backend.app.database.models.video import VideoPrivacyProfile


class VideoProcessorError(RuntimeError):
    """Raised when a video cannot be transformed safely."""


@dataclass(frozen=True)
class VideoProcessingResult:
    """Private processing measurements used to build a safe job response."""

    duration_seconds: float
    fps: float
    width: int
    height: int
    frame_count: int
    detected_frames: int
    quality_flags: list[str]
    usable: bool
    needs_review: bool = False


class VideoPrivacyProcessor:
    """Transform video by redacting faces and blurring detector misses."""

    @staticmethod
    def _stream_metadata(capture) -> dict[str, float | int]:
        """Validate bounded stream metadata without trusting it for frame count."""

        cv2: Any = import_module("cv2")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if (
            not math.isfinite(fps)
            or fps < VIDEO_MIN_FPS
            or fps > VIDEO_MAX_FPS
        ):
            raise VideoProcessorError("Video frame rate is outside the safe range.")
        if (
            width <= 0
            or height <= 0
            or width > VIDEO_MAX_WIDTH
            or height > VIDEO_MAX_HEIGHT
            or width * height > VIDEO_MAX_WIDTH * VIDEO_MAX_HEIGHT
        ):
            raise VideoProcessorError("Video dimensions exceed the safe range.")
        if frame_count < 0 or frame_count > VIDEO_MAX_FRAMES:
            raise VideoProcessorError("Video contains too many frames.")
        if frame_count > 0 and frame_count / fps > VIDEO_MAX_DURATION_SECONDS:
            raise VideoProcessorError("Video exceeds the configured duration limit.")
        return {"fps": fps, "width": width, "height": height, "frame_count": frame_count}

    @staticmethod
    def _check_deadline(deadline: float | None) -> None:
        if deadline is not None and time.monotonic() > deadline:
            raise VideoProcessorError("Video preflight timed out.")

    @staticmethod
    def preflight(source_path: Path, *, deadline: float | None = None) -> dict[str, float | int]:
        """Validate that a readable video stream exists before queueing work."""

        try:
            cv2: Any = import_module("cv2")
        except ImportError as exc:
            raise VideoProcessorError("Video privacy runtime is unavailable.") from exc
        VideoPrivacyProcessor._check_deadline(deadline)
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            capture.release()
            raise VideoProcessorError("Video stream could not be opened.")
        try:
            metadata = VideoPrivacyProcessor._stream_metadata(capture)
        except VideoProcessorError:
            capture.release()
            raise
        VideoPrivacyProcessor._check_deadline(deadline)
        readable, _ = capture.read()
        capture.release()
        if not readable:
            raise VideoProcessorError("Video contains no readable frames.")
        return metadata

    def process(
        self,
        source_path: Path,
        output_path: Path,
        preview_path: Path,
        profile: VideoPrivacyProfile,
    ) -> VideoProcessingResult:
        """Read, transform, and validate one video."""

        try:
            cv2: Any = import_module("cv2")
        except ImportError as exc:
            raise VideoProcessorError("Video privacy runtime is unavailable.") from exc

        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            capture.release()
            raise VideoProcessorError("Video stream could not be opened.")

        try:
            metadata = self._stream_metadata(capture)
        except VideoProcessorError:
            capture.release()
            raise
        fps = float(metadata["fps"])
        width = int(metadata["width"])
        height = int(metadata["height"])

        if output_path.is_symlink() or preview_path.is_symlink():
            capture.release()
            raise VideoProcessorError("Video output path is invalid.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            capture.release()
            raise VideoProcessorError("Transformed video could not be encoded.")

        if profile != VideoPrivacyProfile.FACE_REDACTED:
            capture.release()
            writer.release()
            raise VideoProcessorError("Face redaction is the only available privacy transform.")
        cascade = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        face_detector = cv2.CascadeClassifier(str(cascade))
        if face_detector.empty():
            capture.release()
            writer.release()
            raise VideoProcessorError("Face-redaction runtime is unavailable.")

        frame_count = 0
        detected_frames = 0
        preview_frame: np.ndarray | None = None
        started_at = time.monotonic()
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if (
                    time.monotonic() - started_at > VIDEO_PRIVACY_TIMEOUT_SECONDS
                    or frame_count >= VIDEO_MAX_FRAMES
                ):
                    raise VideoProcessorError("Video privacy processing exceeded its limit.")
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                expected_timestamp = frame_count / fps
                if not math.isfinite(timestamp) or abs(timestamp - expected_timestamp) > max(0.05, 1 / fps):
                    raise VideoProcessorError("Video timing is not constant.")
                frame_count += 1
                transformed, detected = self._transform_frame(
                    cv2, frame, profile, face_detector=face_detector
                )
                detected_frames += int(detected)
                writer.write(transformed)
                if output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES:
                    raise VideoProcessorError("Transformed video exceeds the output limit.")
                if preview_frame is None:
                    preview_frame = transformed.copy()
            if frame_count == 0 or preview_frame is None:
                raise VideoProcessorError("Video contains no readable frames.")
            if frame_count / fps > VIDEO_MAX_DURATION_SECONDS:
                raise VideoProcessorError("Video exceeds the configured duration limit.")
        finally:
            capture.release()
            writer.release()


        if not cv2.imwrite(str(preview_path), preview_frame):
            raise VideoProcessorError("Privacy preview could not be encoded.")
        if (
            not output_path.exists()
            or output_path.stat().st_size == 0
            or output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES
        ):
            raise VideoProcessorError("Transformed video failed output validation.")
        validation_capture = cv2.VideoCapture(str(output_path))
        validated_frames = 0
        validation_started_at = time.monotonic()
        while True:
            output_ok, output_frame = validation_capture.read()
            if not output_ok:
                break
            if (
                time.monotonic() - validation_started_at > VIDEO_PRIVACY_TIMEOUT_SECONDS
                or validated_frames >= VIDEO_MAX_FRAMES
            ):
                validation_capture.release()
                raise VideoProcessorError("Transformed video validation exceeded its limit.")
            if output_frame.shape[1] != width or output_frame.shape[0] != height:
                validation_capture.release()
                raise VideoProcessorError("Transformed video dimensions changed.")
            validated_frames += 1
        validation_capture.release()
        if validated_frames == 0 or validated_frames != frame_count:
            raise VideoProcessorError("Transformed video failed output validation.")

        coverage = detected_frames / max(frame_count, 1)
        flags: list[str] = []
        if detected_frames == 0:
            flags.append("no_detection")
        elif coverage < 0.8:
            flags.append("intermittent_detection")
        # A redacted fallback is still privacy-safe, but reviewers should know
        # that the detector did not provide continuous evidence.
        usable = coverage >= 0.5
        if profile == VideoPrivacyProfile.POSE_ONLY:
            usable = coverage > 0
        needs_review = usable and bool(flags)
        return VideoProcessingResult(
            duration_seconds=frame_count / fps,
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
            detected_frames=detected_frames,
            quality_flags=flags,
            usable=usable,
            needs_review=needs_review,
        )

    @staticmethod
    def _transform_frame(cv2, frame, profile, *, face_detector, pose=None):
        if profile != VideoPrivacyProfile.FACE_REDACTED:
            raise VideoProcessorError("Face redaction is the only available privacy transform.")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
        # A missing or ambiguous face detection is not safe to pass through as
        # a partially redacted frame.
        if len(faces) != 1:
            return cv2.GaussianBlur(frame, (0, 0), sigmaX=19, sigmaY=19), False
        transformed = cv2.GaussianBlur(frame, (0, 0), sigmaX=19, sigmaY=19)
        return transformed, True
