"""Render a privacy-safe review video from one shared pose-estimation pass."""

from __future__ import annotations

from bisect import bisect_right
import json
from importlib import import_module
from pathlib import Path
import math
import shutil
import subprocess  # nosec B404
import time
from typing import Any

import numpy as np

from backend.app.video_detection.contract import DetectionError
from backend.app.core.config import (
    VIDEO_MAX_FRAMES,
    VIDEO_MAX_HEIGHT,
    VIDEO_MAX_OUTPUT_BYTES,
    VIDEO_MAX_WIDTH,
    VIDEO_MAX_FPS,
    VIDEO_MIN_FPS,
    VIDEO_PRIVACY_TIMEOUT_SECONDS,
)

# Lightweight OpenPose's COCO order: nose, neck, shoulders, arms, hips, legs,
# then eyes and ears. These are only visualization edges; they are not model
# preprocessing inputs.
SKELETON_EDGES = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (1, 5),
    (5, 6),
    (6, 7),
    (1, 8),
    (8, 9),
    (9, 10),
    (1, 11),
    (11, 12),
    (12, 13),
    (0, 14),
    (14, 16),
    (0, 15),
    (15, 17),
)


def validate_visualization_artifact(
    path: Path,
    *,
    expected_fps: float | None = None,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_frame_count: int | None = None,
    expected_duration: float | None = None,
) -> None:
    """Fail closed unless the rendered artifact is an audio-free video."""

    if not path.is_file() or path.is_symlink():
        raise DetectionError("visualization_failed")
    if path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES:
        raise DetectionError("visualization_failed")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise DetectionError("visualization_failed")
    try:
        # The executable and path are server-generated; no shell is used.
        inspected = subprocess.run(  # nosec B603
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height,avg_frame_rate,nb_read_frames,nb_frames",
                "-count_frames",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        payload = json.loads(inspected.stdout)
    except (
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise DetectionError("visualization_failed") from exc
    if inspected.returncode != 0:
        raise DetectionError("visualization_failed")
    streams = payload.get("streams")
    format_data = payload.get("format")
    if (
        not isinstance(streams, list)
        or not all(isinstance(stream, dict) for stream in streams)
        or not isinstance(format_data, dict)
    ):
        raise DetectionError("visualization_failed")
    video_streams = [
        stream for stream in streams if stream.get("codec_type") == "video"
    ]
    if len(video_streams) != 1 or any(
        stream.get("codec_type") == "audio" for stream in streams
    ):
        raise DetectionError("visualization_failed")
    video = video_streams[0]
    try:
        duration = float(format_data.get("duration", 0))
        width = int(video.get("width", 0))
        height = int(video.get("height", 0))
    except (TypeError, ValueError) as exc:
        raise DetectionError("visualization_failed") from exc
    if width <= 0 or height <= 0 or not math.isfinite(duration) or duration <= 0:
        raise DetectionError("visualization_failed")
    if expected_width is not None and width != expected_width:
        raise DetectionError("visualization_failed")
    if expected_height is not None and height != expected_height:
        raise DetectionError("visualization_failed")
    if expected_duration is not None and abs(duration - expected_duration) > max(
        0.1, 1 / max(expected_fps or 1, 1)
    ):
        raise DetectionError("visualization_failed")
    if expected_fps is not None:
        try:
            numerator, denominator = str(video.get("avg_frame_rate", "0/0")).split("/", 1)
            actual_fps = float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            raise DetectionError("visualization_failed") from exc
        if not math.isclose(actual_fps, expected_fps, rel_tol=0.01, abs_tol=0.01):
            raise DetectionError("visualization_failed")
    if expected_frame_count is not None:
        try:
            actual_frame_count = int(video.get("nb_read_frames", video.get("nb_frames", 0)))
        except (TypeError, ValueError) as exc:
            raise DetectionError("visualization_failed") from exc
        if actual_frame_count != expected_frame_count:
            raise DetectionError("visualization_failed")


def _mask_frame(cv2: Any, frame: np.ndarray, keypoints: np.ndarray | None) -> np.ndarray:
    """Blur every source pixel before adding the non-identifying pose overlay."""

    _ = keypoints
    height, width = frame.shape[:2]
    sigma = max(25.0, min(width, height) * 0.04)
    return cv2.GaussianBlur(frame, (0, 0), sigmaX=sigma, sigmaY=sigma)


def _draw_pose(cv2: Any, frame: np.ndarray, keypoints: np.ndarray | None) -> None:
    """Draw the same 18 keypoints that fed the model's 15-point representation."""

    if keypoints is None or keypoints.shape != (18, 3):
        return
    thickness = max(2, frame.shape[1] // 640)
    for start, end in SKELETON_EDGES:
        if keypoints[start, 2] < 0.1 or keypoints[end, 2] < 0.1:
            continue
        first = tuple(np.round(keypoints[start, :2]).astype(int))
        second = tuple(np.round(keypoints[end, :2]).astype(int))
        cv2.line(frame, first, second, (193, 179, 0), thickness, cv2.LINE_AA)
    for x, y, confidence in keypoints:
        if confidence < 0.1:
            continue
        cv2.circle(
            frame,
            (int(round(x)), int(round(y))),
            max(3, thickness + 1),
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )
        cv2.circle(
            frame,
            (int(round(x)), int(round(y))),
            max(2, thickness),
            (193, 179, 0),
            -1,
            cv2.LINE_AA,
        )


def _overlay(cv2: Any, frame: np.ndarray, timestamp: float) -> None:
    """Add non-identifying review context to the protected frame."""

    overlay = frame.copy()
    cv2.rectangle(overlay, (20, 20), (610, 88), (16, 25, 31), -1)
    cv2.addWeighted(overlay, 0.86, frame, 0.14, 0, frame)
    cv2.putText(
        frame,
        "PRIVACY-SAFE REVIEW",
        (38, 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Skeleton overlay · no audio · research only",
        (38, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (193, 179, 0),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"{timestamp // 60:02.0f}:{timestamp % 60:04.1f}",
        (frame.shape[1] - 140, frame.shape[0] - 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def render_visualization(
    source_path: Path,
    output_path: Path,
    pose_samples: list[tuple[float, np.ndarray]],
) -> dict[str, Any]:
    """Create a video-only, masked, skeleton-overlaid review artifact."""

    try:
        cv2: Any = import_module("cv2")
    except ImportError as exc:
        raise DetectionError("visualization_failed") from exc
    if not pose_samples:
        raise DetectionError("visualization_failed")

    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        capture.release()
        raise DetectionError("visualization_failed")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if (
        not math.isfinite(fps)
        or fps < VIDEO_MIN_FPS
        or fps > VIDEO_MAX_FPS
        or width <= 0
        or height <= 0
        or width > VIDEO_MAX_WIDTH
        or height > VIDEO_MAX_HEIGHT
        or width * height > VIDEO_MAX_WIDTH * VIDEO_MAX_HEIGHT
    ):
        capture.release()
        raise DetectionError("visualization_failed")
    if output_path.is_symlink():
        capture.release()
        raise DetectionError("visualization_failed")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise DetectionError("visualization_failed")

    sample_times = [sample[0] for sample in pose_samples]
    sample_index = 0
    frame_index = 0
    started_at = time.monotonic()
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if (
                time.monotonic() - started_at > VIDEO_PRIVACY_TIMEOUT_SECONDS
                or frame_index >= VIDEO_MAX_FRAMES
            ):
                raise DetectionError("visualization_failed")
            timestamp = frame_index / fps
            frame_index += 1
            sample_index = min(
                max(0, bisect_right(sample_times, timestamp) - 1),
                len(pose_samples) - 1,
            )
            sample_time, keypoints = pose_samples[sample_index]
            # Do not draw stale pose data across a large decode gap.
            pose = keypoints if abs(timestamp - sample_time) <= 1.0 else None
            protected = _mask_frame(cv2, frame, pose)
            _draw_pose(cv2, protected, pose)
            _overlay(cv2, protected, timestamp)
            writer.write(protected)
            if output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES:
                raise DetectionError("visualization_failed")
    finally:
        capture.release()
        writer.release()

    if (
        frame_index == 0
        or not output_path.exists()
        or output_path.stat().st_size == 0
        or output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES
    ):
        raise DetectionError("visualization_failed")
    return {
        "available": True,
        "media_type": "video/mp4",
        "audio_included": False,
        "privacy_method": "full-frame-blur-and-skeleton-overlay",
        "frame_count": frame_index,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": frame_index / fps,
        "overlay": {
            "skeleton": True,
            "model_score": False,
            "event_markers": False,
        },
        "frontend_overlay": {"model_score": True, "event_markers": True},
    }
