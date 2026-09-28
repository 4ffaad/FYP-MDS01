"""Fail-closed OpenCV adapter for the privacy-only video transform."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import json
import math
import os
from pathlib import Path
import subprocess  # nosec B404
import sys
import tempfile
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


def video_worker_environment() -> dict[str, str]:
    """Return only paths and runtime knobs required by isolated video workers."""

    temp_root = Path(tempfile.gettempdir())
    repository_root = Path(__file__).resolve().parents[3]
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "PYTHONPATH": str(repository_root),
        "HOME": str(temp_root),
        "TMPDIR": str(temp_root),
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
        "XDG_CACHE_HOME": str(temp_root / "xdg-cache"),
        "MPLCONFIGDIR": str(temp_root / "matplotlib"),
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "NUMEXPR_NUM_THREADS": "2",
    }
    for name in (
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
        "VSVIG_ASSET_DIR",
        "VSVIG_CONTRACT_SHA256",
        "MDS01_NNPACK_ENABLED",
    ):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


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
    pose_detected_frames: int | None = None
    pose_sampled_frames: int | None = None


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
    def _quality_assessment(
        detected_frames: int,
        frame_count: int,
        *,
        allow_full_blur_fallback: bool = False,
    ) -> tuple[list[str], bool, bool]:
        """Keep a full-frame-blurred output reviewable when face coverage is low."""

        coverage = detected_frames / max(frame_count, 1)
        flags: list[str] = []
        if detected_frames == 0:
            flags.append("no_detection")
        elif coverage < 0.8:
            flags.append("intermittent_detection")
        usable = coverage >= 0.5 or allow_full_blur_fallback
        needs_review = usable and bool(flags)
        return flags, usable, needs_review

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
        try:
            VideoPrivacyProcessor._check_deadline(deadline)
            readable, _ = capture.read()
            VideoPrivacyProcessor._check_deadline(deadline)
        finally:
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
    ) -> dict[str, float | int | str | list[int]]:
        """Create a bounded native or explicitly opted-in letterboxed model source."""

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
        resized_width, resized_height, pad_x, pad_y = model_frame_layout(
            source_width, source_height
        )
        adaptation = (source_width, source_height) != (
            VSVIG_INPUT_WIDTH,
            VSVIG_INPUT_HEIGHT,
        )
        if adaptation and not allow_letterbox_adaptation:
            capture.release()
            raise VideoProcessorError(
                "Source video must match the reviewed 1920x1080 VSViG geometry."
            )
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
                if frame.shape[:2] != (source_height, source_width):
                    raise VideoProcessorError("Decoded frame geometry changed unexpectedly.")
                if adaptation:
                    resized = cv2.resize(
                        frame,
                        (resized_width, resized_height),
                        interpolation=(
                            cv2.INTER_LINEAR
                            if resized_width >= source_width
                            and resized_height >= source_height
                            else cv2.INTER_AREA
                        ),
                    )
                    model_frame = np.zeros(
                        (VSVIG_INPUT_HEIGHT, VSVIG_INPUT_WIDTH, 3), dtype=np.uint8
                    )
                    model_frame[
                        pad_y : pad_y + resized_height,
                        pad_x : pad_x + resized_width,
                    ] = resized
                else:
                    model_frame = frame
                writer.write(model_frame)
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
            "adaptation": "letterbox" if adaptation else "none",
            "source_timestamp_offset_seconds": float(timestamp_origin or 0.0),
            "pad_x": pad_x if adaptation else 0,
            "pad_y": pad_y if adaptation else 0,
            "padding_ltrb": [
                pad_x if adaptation else 0,
                pad_y if adaptation else 0,
                VSVIG_INPUT_WIDTH - resized_width - pad_x if adaptation else 0,
                VSVIG_INPUT_HEIGHT - resized_height - pad_y if adaptation else 0,
            ],
        }

    def process(
        self,
        source_path: Path,
        output_path: Path,
        preview_path: Path,
        profile: VideoPrivacyProfile,
        *,
        allow_full_blur_fallback: bool = False,
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


        expected_frame_count = int(metadata["frame_count"])
        if expected_frame_count > 0 and frame_count != expected_frame_count:
            raise VideoProcessorError("Video could not be decoded completely.")
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

        # Full-frame blur is applied independently of detection; the preview-only
        # pose workflow may retain that stronger fallback, but marks it for review.
        flags, usable, needs_review = VideoPrivacyProcessor._quality_assessment(
            detected_frames,
            frame_count,
            allow_full_blur_fallback=allow_full_blur_fallback,
        )
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


def preflight_video_subprocess(
    source_path: Path,
    *,
    timeout_seconds: float,
) -> dict[str, float | int]:
    """Validate a video in a killable process with a bounded metadata result."""

    timeout = float(timeout_seconds)
    if not math.isfinite(timeout) or timeout <= 0:
        raise VideoProcessorError("Video preflight timed out.")
    if source_path.is_symlink() or not source_path.is_file():
        raise VideoProcessorError("Video stream could not be opened.")

    descriptor, result_name = tempfile.mkstemp(
        prefix=".video-preflight-",
        suffix=".json",
        dir=source_path.parent,
    )
    os.close(descriptor)
    result_path = Path(result_name)
    result_path.unlink()
    try:
        subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "backend.app.video_privacy.processor",
                "--preflight-worker",
                str(source_path),
                str(result_path),
                str(timeout),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=True,
            env=video_worker_environment(),
        )
        if (
            result_path.is_symlink()
            or not result_path.is_file()
            or result_path.stat().st_size > 16 * 1024
        ):
            raise VideoProcessorError("Video preflight worker returned invalid metadata.")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise VideoProcessorError("Video preflight worker returned invalid metadata.")
        fps = payload.get("fps")
        width = payload.get("width")
        height = payload.get("height")
        frame_count = payload.get("frame_count")
        if (
            not isinstance(fps, (int, float))
            or isinstance(fps, bool)
            or not math.isfinite(float(fps))
            or float(fps) <= 0
            or type(width) is not int
            or width <= 0
            or type(height) is not int
            or height <= 0
            or type(frame_count) is not int
            or frame_count <= 0
        ):
            raise VideoProcessorError("Video preflight worker returned invalid metadata.")
        return {
            "fps": float(fps),
            "width": width,
            "height": height,
            "frame_count": frame_count,
        }
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessorError("Video preflight timed out.") from exc
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise VideoProcessorError("Video stream could not be validated safely.") from exc
    finally:
        result_path.unlink(missing_ok=True)


def _run_preflight_worker(source_path: str, result_path: str, timeout_text: str) -> int:
    """Entry point for the isolated OpenCV preflight process."""

    source = Path(source_path)
    result = Path(result_path)
    timeout = float(timeout_text)
    if (
        source.is_symlink()
        or not source.is_file()
        or result.is_symlink()
        or result.exists()
        or source.parent != result.parent
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        return 2
    try:
        metadata = VideoPrivacyProcessor.preflight(
            source,
            deadline=time.monotonic() + timeout,
        )
        descriptor = os.open(
            result,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(metadata, output, allow_nan=False)
        return 0
    except Exception:
        result.unlink(missing_ok=True)
        return 1


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--preflight-worker":
        raise SystemExit(_run_preflight_worker(sys.argv[2], sys.argv[3], sys.argv[4]))
    raise SystemExit(2)
