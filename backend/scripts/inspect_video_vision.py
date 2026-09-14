"""Inspect face/pose detection on one approved local video.

This is a diagnostic tool, not the production privacy transform. Keep the
annotated output outside Git because it contains the source appearance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def clamp_box(x: int, y: int, width: int, height: int, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
    left = max(0, min(x, frame_width - 1))
    top = max(0, min(y, frame_height - 1))
    right = max(left + 1, min(x + width, frame_width))
    bottom = max(top + 1, min(y + height, frame_height))
    return left, top, right - left, bottom - top


def inspect(input_path: Path, output_path: Path, mode: str, print_every: int) -> dict:
    import cv2

    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise SystemExit("Could not open the video.")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise SystemExit("Video metadata is invalid.")

    haar = None
    if mode in {"haar", "both"}:
        haar = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
        if haar.empty():
            capture.release()
            raise SystemExit("OpenCV Haar cascade is unavailable.")

    mediapipe = None
    face_detection = None
    pose = None
    if mode in {"mediapipe", "both", "pose"}:
        try:
            import mediapipe as mediapipe
        except ImportError as exc:
            capture.release()
            raise SystemExit("MediaPipe is unavailable in this runtime.") from exc
        if mode in {"mediapipe", "both"}:
            face_detection = mediapipe.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5
            )
        if mode == "pose":
            pose = mediapipe.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise SystemExit("Could not create the annotated output video.")

    counts = {"frames": 0, "haar_face_frames": 0, "mediapipe_face_frames": 0, "pose_frames": 0}
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            counts["frames"] += 1
            annotated = frame.copy()
            haar_faces = []
            mediapipe_faces = []
            pose_found = False

            if haar is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                haar_faces = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
                for x, y, box_width, box_height in haar_faces:
                    cv2.rectangle(annotated, (x, y), (x + box_width, y + box_height), (0, 255, 0), 3)

            if face_detection is not None:
                result = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                for detection in result.detections or []:
                    box = detection.location_data.relative_bounding_box
                    x, y = round(box.xmin * width), round(box.ymin * height)
                    box_width, box_height = round(box.width * width), round(box.height * height)
                    x, y, box_width, box_height = clamp_box(x, y, box_width, box_height, width, height)
                    mediapipe_faces.append((x, y, box_width, box_height))
                    cv2.rectangle(
                        annotated, (x, y), (x + box_width, y + box_height), (255, 100, 0), 3
                    )

            if pose is not None:
                result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pose_found = bool(result.pose_landmarks)
                if pose_found:
                    mediapipe.solutions.drawing_utils.draw_landmarks(
                        annotated, result.pose_landmarks, mediapipe.solutions.pose.POSE_CONNECTIONS
                    )

            counts["haar_face_frames"] += int(len(haar_faces) > 0)
            counts["mediapipe_face_frames"] += int(bool(mediapipe_faces))
            counts["pose_frames"] += int(pose_found)
            writer.write(annotated)

            if counts["frames"] == 1 or counts["frames"] % print_every == 0:
                print(
                    f"frame={counts['frames']:>5} time={counts['frames'] / fps:>7.2f}s "
                    f"haar_faces={len(haar_faces):>2} mediapipe_faces={len(mediapipe_faces):>2} "
                    f"pose={'yes' if pose_found else 'no'}",
                    flush=True,
                )
    finally:
        capture.release()
        writer.release()
        if face_detection is not None:
            face_detection.close()
        if pose is not None:
            pose.close()

    counts["fps"] = fps
    counts["width"] = width
    counts["height"] = height
    counts["output"] = str(output_path)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Approved local video to inspect")
    parser.add_argument("--output", type=Path, default=Path("/tmp/mds01-vision-check.mp4"))
    parser.add_argument("--mode", choices=("haar", "mediapipe", "both", "pose"), default="both")
    parser.add_argument("--print-every", type=int, default=25, metavar="N")
    args = parser.parse_args()
    if args.print_every < 1:
        parser.error("--print-every must be positive")
    print(f"MDS01 computer-vision inspection: mode={args.mode}")
    print("Diagnostic only: keep the annotated output local and outside Git.")
    summary = inspect(args.video, args.output, args.mode, args.print_every)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
