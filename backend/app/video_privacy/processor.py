"""Fail-closed OpenCV/MediaPipe adapters for privacy-only video transforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.app.core.config import VIDEO_MAX_DURATION_SECONDS
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
    """Transform video without retaining the original appearance for pose mode."""

    @staticmethod
    def preflight(source_path: Path) -> dict[str, float | int]:
        """Validate that a readable video stream exists before queueing work."""

        try:
            import cv2
        except ImportError as exc:
            raise VideoProcessorError("Video privacy runtime is unavailable.") from exc
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            capture.release()
            raise VideoProcessorError("Video stream could not be opened.")
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or width <= 0 or height <= 0:
            capture.release()
            raise VideoProcessorError("Video stream metadata is invalid.")
        if frame_count > 0 and frame_count / fps > VIDEO_MAX_DURATION_SECONDS:
            capture.release()
            raise VideoProcessorError("Video exceeds the configured duration limit.")
        readable, _ = capture.read()
        capture.release()
        if not readable:
            raise VideoProcessorError("Video contains no readable frames.")
        return {"fps": fps, "width": width, "height": height, "frame_count": frame_count}

    def process(
        self,
        source_path: Path,
        output_path: Path,
        preview_path: Path,
        profile: VideoPrivacyProfile,
    ) -> VideoProcessingResult:
        """Read, transform, and validate one video using optional runtimes."""

        try:
            import cv2
        except ImportError as exc:
            raise VideoProcessorError("Video privacy runtime is unavailable.") from exc

        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            capture.release()
            raise VideoProcessorError("Video stream could not be opened.")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        reported_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or width <= 0 or height <= 0:
            capture.release()
            raise VideoProcessorError("Video stream metadata is invalid.")
        if reported_count > 0 and reported_count / fps > VIDEO_MAX_DURATION_SECONDS:
            capture.release()
            raise VideoProcessorError("Video exceeds the configured duration limit.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            capture.release()
            raise VideoProcessorError("Transformed video could not be encoded.")

        face_detector = None
        pose = None
        if profile == VideoPrivacyProfile.FACE_REDACTED:
            cascade = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            face_detector = cv2.CascadeClassifier(str(cascade))
            if face_detector.empty():
                capture.release()
                writer.release()
                raise VideoProcessorError("Face-redaction runtime is unavailable.")
        elif profile == VideoPrivacyProfile.POSE_ONLY:
            try:
                import mediapipe as mp
            except ImportError as exc:
                capture.release()
                writer.release()
                raise VideoProcessorError("Pose privacy runtime is unavailable.") from exc
            pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=0,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        else:
            capture.release()
            writer.release()
            raise VideoProcessorError("Privacy profile is unsupported.")

        frame_count = 0
        detected_frames = 0
        preview_frame: np.ndarray | None = None
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_count += 1
                transformed, detected = self._transform_frame(
                    cv2, frame, profile, face_detector=face_detector, pose=pose
                )
                detected_frames += int(detected)
                writer.write(transformed)
                if preview_frame is None:
                    preview_frame = transformed.copy()
            if frame_count == 0 or preview_frame is None:
                raise VideoProcessorError("Video contains no readable frames.")
            if frame_count / fps > VIDEO_MAX_DURATION_SECONDS:
                raise VideoProcessorError("Video exceeds the configured duration limit.")
        finally:
            capture.release()
            writer.release()
            if pose is not None:
                pose.close()

        if not cv2.imwrite(str(preview_path), preview_frame):
            raise VideoProcessorError("Privacy preview could not be encoded.")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoProcessorError("Transformed video failed output validation.")
        validation_capture = cv2.VideoCapture(str(output_path))
        validated_frames = 0
        while True:
            output_ok, output_frame = validation_capture.read()
            if not output_ok:
                break
            if output_frame.shape[1] != width or output_frame.shape[0] != height:
                validation_capture.release()
                raise VideoProcessorError("Transformed video dimensions changed.")
            validated_frames += 1
        validation_capture.release()
        if validated_frames == 0 or abs(validated_frames - frame_count) > max(1, int(frame_count * 0.05)):
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
            frame_count=max(frame_count, reported_count),
            detected_frames=detected_frames,
            quality_flags=flags,
            usable=usable,
            needs_review=needs_review,
        )

    @staticmethod
    def _transform_frame(cv2, frame, profile, *, face_detector, pose):
        if profile == VideoPrivacyProfile.FACE_REDACTED:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
            # Keep the face profile fail-closed: detector misses must not let
            # an unblurred face pass through merely because another face was
            # detected in the same frame.
            transformed = cv2.GaussianBlur(frame, (0, 0), sigmaX=19, sigmaY=19)
            for x, y, w, h in faces:
                roi = transformed[y : y + h, x : x + w]
                transformed[y : y + h, x : x + w] = cv2.GaussianBlur(roi, (0, 0), sigmaX=25, sigmaY=25)
            return transformed, len(faces) > 0

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)
        canvas = np.zeros_like(frame)
        if not result.pose_landmarks:
            return canvas, False
        mp_drawing = __import__("mediapipe").solutions.drawing_utils
        mp_pose = __import__("mediapipe").solutions.pose
        mp_drawing.draw_landmarks(canvas, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        return canvas, True
