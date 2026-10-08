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
FACE_KEYPOINTS = (0, 14, 15, 16, 17)


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
                "format=duration:stream=codec_type,codec_name,pix_fmt,width,height,avg_frame_rate,nb_read_frames,nb_frames",
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
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        raise DetectionError("visualization_failed")
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


def _mask_frame(cv2: Any, frame: np.ndarray) -> np.ndarray:
    """Blur every pixel when the tracked face is uncertain."""
    height, width = frame.shape[:2]
    sigma = max(25.0, min(width, height) * 0.04)
    return cv2.GaussianBlur(frame, (0, 0), sigmaX=sigma, sigmaY=sigma)


def _redact_face(
    cv2: Any,
    frame: np.ndarray,
    keypoints: np.ndarray | None,
) -> tuple[np.ndarray, bool]:
    """Blur the tracked face, falling back to the full frame if head landmarks fail."""

    try:
        if keypoints is None or keypoints.shape != (18, 3):
            raise ValueError("tracked-face landmarks are unavailable")
        points = keypoints[list(FACE_KEYPOINTS)]
        height, frame_width = frame.shape[:2]
        valid = (
            (points[:, 2] >= 0.1)
            & np.isfinite(points).all(axis=1)
            & (points[:, 0] >= 0)
            & (points[:, 0] < frame_width)
            & (points[:, 1] >= 0)
            & (points[:, 1] < height)
        )
        if not valid.all():
            raise ValueError("tracked-face landmarks are incomplete")
        nose, left_eye, right_eye, left_ear, right_ear = points[:, :2]
        face_width = max(
            float(np.linalg.norm(left_ear - right_ear)),
            float(np.linalg.norm(left_eye - right_eye)) * 1.6,
        )
        if not math.isfinite(face_width) or face_width < 20:
            raise ValueError("tracked-face region is too small")
        eye_line = float((left_eye[1] + right_eye[1]) / 2)
        left = int(math.floor(min(left_ear[0], right_ear[0]) - face_width * 0.4))
        right = int(math.ceil(max(left_ear[0], right_ear[0]) + face_width * 0.4))
        top = int(math.floor(min(eye_line, nose[1]) - face_width * 0.8))
        bottom = int(math.ceil(max(eye_line, nose[1]) + face_width * 1.2))
        left, top = max(0, left), max(0, top)
        right, bottom = min(frame_width, right), min(height, bottom)
        if right <= left or bottom <= top:
            raise ValueError("tracked-face region is invalid")
        if (right - left) * (bottom - top) > frame_width * height * 0.55:
            raise ValueError("tracked-face region covers most of the frame")
        redacted = frame.copy()
        region = redacted[top:bottom, left:right]
        if region.shape[0] < 24 or region.shape[1] < 24:
            raise ValueError("tracked-face region is too small")
        sigma = max(16.0, min(region.shape[:2]) * 0.25)
        redacted[top:bottom, left:right] = cv2.GaussianBlur(
            region, (0, 0), sigmaX=sigma, sigmaY=sigma
        )
        return redacted, True
    except Exception:
        return _mask_frame(cv2, frame), False


def _draw_pose(
    cv2: Any,
    frame: np.ndarray,
    keypoints: np.ndarray | None,
    *,
    label: str = "Track 1",
    color: tuple[int, int, int] = (193, 179, 0),
) -> None:
    """Draw one detected person without implying that the track is the patient."""

    if keypoints is None or keypoints.shape != (18, 3):
        return
    thickness = max(2, frame.shape[1] // 640)
    for start, end in SKELETON_EDGES:
        if keypoints[start, 2] < 0.1 or keypoints[end, 2] < 0.1:
            continue
        first = tuple(np.round(keypoints[start, :2]).astype(int))
        second = tuple(np.round(keypoints[end, :2]).astype(int))
        cv2.line(frame, first, second, color, thickness, cv2.LINE_AA)
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
            color,
            -1,
            cv2.LINE_AA,
        )
    visible = keypoints[(keypoints[:, 2] >= 0.1) & np.isfinite(keypoints).all(axis=1)]
    if len(visible):
        x = max(0, int(visible[:, 0].min()))
        y = max(18, int(visible[:, 1].min()) - 8)
        cv2.putText(
            frame,
            label,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )


def _pose_at_time(
    pose_samples: list[tuple[float, np.ndarray]], sample_times: list[float], timestamp: float
) -> np.ndarray | None:
    """Interpolate adjacent tracked poses; reject stale or malformed samples."""

    if not sample_times:
        return None
    right = bisect_right(sample_times, timestamp)
    if right == 0:
        return pose_samples[0][1] if sample_times[0] - timestamp <= 1 / 6 + 1e-6 else None
    if right == len(sample_times):
        return pose_samples[-1][1] if timestamp - sample_times[-1] <= 1 / 6 + 1e-6 else None
    left_time, left = pose_samples[right - 1]
    right_time, next_pose = pose_samples[right]
    gap = right_time - left_time
    if gap <= 0 or gap > 0.25 or left.shape != (18, 3) or next_pose.shape != (18, 3):
        return None
    if timestamp - left_time <= 1e-6:
        return left
    fraction = (timestamp - left_time) / gap
    interpolated = left.copy()
    valid = (left[:, 2] >= 0.1) & (next_pose[:, 2] >= 0.1)
    interpolated[valid, :2] = (
        left[valid, :2] * (1 - fraction) + next_pose[valid, :2] * fraction
    )
    interpolated[valid, 2] = np.minimum(left[valid, 2], next_pose[valid, 2])
    interpolated[~valid, 2] = 0
    return interpolated


def _overlay(
    cv2: Any,
    frame: np.ndarray,
    timestamp: float,
    *,
    pose_detected: bool,
) -> None:
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
        "Body joints overlaid · research only"
        if pose_detected
        else "No body pose detected · research only",
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
    *,
    preview_path: Path | None = None,
    unblurred: bool = False,
) -> dict[str, Any]:
    """Create a face-blurred, skeleton-overlaid review artifact."""

    try:
        cv2: Any = import_module("cv2")
    except ImportError as exc:
        raise DetectionError("visualization_failed") from exc
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
    render_path = output_path.with_name(f".{output_path.stem}.render.mp4")
    if (
        output_path.is_symlink()
        or render_path.is_symlink()
        or (preview_path is not None and preview_path.is_symlink())
    ):
        capture.release()
        raise DetectionError("visualization_failed")
    for candidate in (output_path, render_path):
        if candidate.exists() and not candidate.is_file():
            capture.release()
            raise DetectionError("visualization_failed")
        candidate.unlink(missing_ok=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if preview_path is not None:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(render_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise DetectionError("visualization_failed")

    sample_times = [sample[0] for sample in pose_samples]
    if any(
        not math.isfinite(sample_time)
        for sample_time in sample_times
    ) or any(
        right <= left
        for left, right in zip(sample_times, sample_times[1:])
    ):
        capture.release()
        writer.release()
        render_path.unlink(missing_ok=True)
        raise DetectionError("visualization_failed")
    tracks: dict[str, list[tuple[float, np.ndarray]]] = {}
    for timestamp, poses in pose_samples:
        if isinstance(poses, dict):
            for label, keypoints in poses.items():
                tracks.setdefault(label, []).append((timestamp, keypoints))
        elif isinstance(poses, np.ndarray):
            tracks.setdefault("Track 1", []).append((timestamp, poses))
        else:
            raise DetectionError("visualization_failed")
    frame_index = 0
    face_blurred_frames = 0
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
            visible_tracks = []
            for index, (label, samples) in enumerate(tracks.items()):
                times = [sample[0] for sample in samples]
                pose = _pose_at_time(samples, times, timestamp)
                if pose is not None:
                    color = (
                        (193, 179, 0),
                        (0, 180, 255),
                        (255, 120, 60),
                        (190, 90, 220),
                    )[index % 4]
                    visible_tracks.append((label, pose, color))
            if unblurred:
                protected, face_blurred = frame, False
            elif len(visible_tracks) == 1:
                protected, face_blurred = _redact_face(
                    cv2, frame, visible_tracks[0][1]
                )
            else:
                protected, face_blurred = _mask_frame(cv2, frame), False
            face_blurred_frames += int(face_blurred)
            for label, pose, color in visible_tracks:
                _draw_pose(cv2, protected, pose, label=label, color=color)
            _overlay(
                cv2, protected, timestamp, pose_detected=bool(visible_tracks)
            )
            writer.write(protected)
            if frame_index == 1 and preview_path is not None:
                if not cv2.imwrite(str(preview_path), protected):
                    raise DetectionError("visualization_failed")
                if (
                    not preview_path.is_file()
                    or preview_path.stat().st_size <= 0
                    or preview_path.stat().st_size > 2 * 1024 * 1024
                ):
                    raise DetectionError("visualization_failed")
            if render_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES:
                raise DetectionError("visualization_failed")
    finally:
        capture.release()
        writer.release()

    if (
        frame_index == 0
        or not render_path.exists()
        or render_path.stat().st_size == 0
        or render_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES
    ):
        raise DetectionError("visualization_failed")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        render_path.unlink(missing_ok=True)
        raise DetectionError("visualization_failed")
    try:
        subprocess.run(  # nosec B603
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-n",
                "-i",
                str(render_path),
                "-map",
                "0:v:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-movflags",
                "+faststart",
                "-fs",
                str(VIDEO_MAX_OUTPUT_BYTES),
                str(output_path),
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=VIDEO_PRIVACY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        output_path.unlink(missing_ok=True)
        raise DetectionError("visualization_failed") from exc
    finally:
        render_path.unlink(missing_ok=True)
    if (
        output_path.is_symlink()
        or not output_path.is_file()
        or output_path.stat().st_size == 0
        or output_path.stat().st_size > VIDEO_MAX_OUTPUT_BYTES
    ):
        raise DetectionError("visualization_failed")
    return {
        "available": True,
        "media_type": "video/mp4",
        "audio_included": False,
        "privacy_method": "unblurred-owner-source-and-skeleton-overlay" if unblurred else "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
        "face_blur_coverage": face_blurred_frames / frame_index,
        "full_frame_fallback_frames": 0 if unblurred else frame_index - face_blurred_frames,
        "quality_flags": ["full_frame_fallback_used"]
        if not unblurred and face_blurred_frames < frame_index
        else [],
        "frame_count": frame_index,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": frame_index / fps,
        "pose_overlay_available": any(
            poses if isinstance(poses, dict) else isinstance(poses, np.ndarray)
            for _, poses in pose_samples
        ),
        "pose_sample_count": sum(
            bool(poses) if isinstance(poses, dict) else isinstance(poses, np.ndarray)
            for _, poses in pose_samples
        ),
        "overlay": {
            "skeleton": any(
                poses if isinstance(poses, dict) else isinstance(poses, np.ndarray)
                for _, poses in pose_samples
            ),
            "model_score": False,
            "event_markers": False,
        },
        "frontend_overlay": {"model_score": True, "event_markers": True},
    }
