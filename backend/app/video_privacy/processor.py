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


VSVIG_INPUT_WIDTH = 1920
VSVIG_INPUT_HEIGHT = 1080


def model_frame_layout(width: int, height: int) -> tuple[int, int, int, int]:
    """Return aspect-preserving dimensions and left/top letterbox padding."""

    if width <= 0 or height <= 0:
        raise VideoProcessorError("Video dimensions are invalid.")
    scale = min(VSVIG_INPUT_WIDTH / width, VSVIG_INPUT_HEIGHT / height)
    resized_width = max(1, min(VSVIG_INPUT_WIDTH, round(width * scale)))
    resized_height = max(1, min(VSVIG_INPUT_HEIGHT, round(height * scale)))
    return (
        resized_width,
        resized_height,
        (VSVIG_INPUT_WIDTH - resized_width) // 2,
        (VSVIG_INPUT_HEIGHT - resized_height) // 2,
    )


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
    """Blur every frame in full and track face-detection coverage for review."""

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

    @staticmethod
    def normalize_for_vsvig(
        source_path: Path,
        output_path: Path,
        *,
        deadline: float | None = None,
        allow_letterbox_adaptation: bool = False,
    ) -> dict[str, float | int | str]:
        """Create a bounded, audio-free model source under explicit adaptation policy."""

        try:
            cv2: Any = import_module("cv2")
        except ImportError as exc:
            raise VideoProcessorError("Video privacy runtime is unavailable.") from exc
        if source_path.absolute() == output_path.absolute() or output_path.is_symlink():
            raise VideoProcessorError("Video normalization output path is invalid.")
        VideoPrivacyProcessor._check_deadline(deadline)
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            capture.release()
            raise VideoProcessorError("Video stream could not be opened.")
        writer = None
        try:
            metadata = VideoPrivacyProcessor._stream_metadata(capture)
        except VideoProcessorError:
            capture.release()
            raise
        source_width = int(metadata["width"])
        source_height = int(metadata["height"])
        fps = float(metadata["fps"])
        expected_frames = int(metadata["frame_count"])
        if expected_frames <= 0:
            capture.release()
            raise VideoProcessorError("Video contains no bounded frame count.")
        resized_width, resized_height, pad_x, pad_y = model_frame_layout(source_width, source_height)
        if (
            (source_width, source_height) != (VSVIG_INPUT_WIDTH, VSVIG_INPUT_HEIGHT)
            and not allow_letterbox_adaptation
        ):
            capture.release()
            raise VideoProcessorError("Video resolution adaptation is not approved for this VSViG contract.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        failed = False
        try:
            writer = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (VSVIG_INPUT_WIDTH, VSVIG_INPUT_HEIGHT),
            )
            if not writer.isOpened():
                raise VideoProcessorError("Normalized video could not be encoded.")
            frame_count = 0
            started_at = time.monotonic()
            timestamp_origin: float | None = None
            while True:
                VideoPrivacyProcessor._check_deadline(deadline)
                ok, frame = capture.read()
                if not ok:
                    break
                if (
                    time.monotonic() - started_at > VIDEO_PRIVACY_TIMEOUT_SECONDS
                    or frame_count >= VIDEO_MAX_FRAMES
                ):
                    raise VideoProcessorError("Video normalization exceeded its limit.")
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                if not math.isfinite(timestamp):
                    raise VideoProcessorError("Video timing is not constant.")
                if timestamp_origin is None:
                    if abs(timestamp) > VIDEO_MAX_DURATION_SECONDS:
                        raise VideoProcessorError("Video timestamp origin is outside the safe range.")
                    timestamp_origin = timestamp
                origin = timestamp_origin
                if origin is None:
                    raise VideoProcessorError("Video timestamp origin is unavailable.")
                expected_timestamp = origin + frame_count / fps
                if abs(timestamp - expected_timestamp) > max(0.05, 1 / fps):
                    raise VideoProcessorError("Video timing is not constant.")
                resized = cv2.resize(
                    frame,
                    (resized_width, resized_height),
                    interpolation=cv2.INTER_LINEAR if resized_width >= source_width else cv2.INTER_AREA,
                )
                canvas = np.zeros((VSVIG_INPUT_HEIGHT, VSVIG_INPUT_WIDTH, 3), dtype=np.uint8)
                canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized
                writer.write(canvas)
                frame_count += 1
                if output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES:
                    raise VideoProcessorError("Normalized video exceeds the output limit.")
            if frame_count != expected_frames:
                raise VideoProcessorError("Video could not be decoded completely.")
        except VideoProcessorError:
            failed = True
            raise
        except Exception as exc:
            failed = True
            raise VideoProcessorError("Video normalization failed safely.") from exc
        finally:
            capture.release()
            if writer is not None:
                writer.release()
            if failed:
                output_path.unlink(missing_ok=True)
        try:
            output_metadata = VideoPrivacyProcessor.preflight(output_path, deadline=deadline)
            if (
                int(output_metadata["width"]) != VSVIG_INPUT_WIDTH
                or int(output_metadata["height"]) != VSVIG_INPUT_HEIGHT
                or int(output_metadata["frame_count"]) != expected_frames
                or not math.isclose(float(output_metadata["fps"]), fps, rel_tol=0.01, abs_tol=0.01)
            ):
                raise VideoProcessorError("Normalized video failed output validation.")
        except Exception:
            output_path.unlink(missing_ok=True)
            raise
        return {
            "fps": fps,
            "width": VSVIG_INPUT_WIDTH,
            "height": VSVIG_INPUT_HEIGHT,
            "frame_count": expected_frames,
            "source_width": source_width,
            "source_height": source_height,
            "adaptation": "letterbox" if (source_width, source_height) != (VSVIG_INPUT_WIDTH, VSVIG_INPUT_HEIGHT) else "none",
            "source_timestamp_offset_seconds": float(timestamp_origin or 0.0),
            "pad_x": pad_x,
            "pad_y": pad_y,
        }

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
        timestamp_origin: float | None = None
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
                if not math.isfinite(timestamp):
                    raise VideoProcessorError("Video timing is not constant.")
                if timestamp_origin is None:
                    if abs(timestamp) > VIDEO_MAX_DURATION_SECONDS:
                        raise VideoProcessorError("Video timestamp origin is outside the safe range.")
                    timestamp_origin = timestamp
                origin = timestamp_origin
                if origin is None:
                    raise VideoProcessorError("Video timestamp origin is unavailable.")
                expected_timestamp = origin + frame_count / fps
                if abs(timestamp - expected_timestamp) > max(0.05, 1 / fps):
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
        # Detection changes the coverage signal, not the blur extent: every
        # frame receives full-frame Gaussian blur.
        if len(faces) != 1:
            return cv2.GaussianBlur(frame, (0, 0), sigmaX=19, sigmaY=19), False
        transformed = cv2.GaussianBlur(frame, (0, 0), sigmaX=19, sigmaY=19)
        return transformed, True
