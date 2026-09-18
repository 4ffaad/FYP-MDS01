"""Inspect Haar face detection on one approved local video.

This is a diagnostic tool, not the production privacy transform. Keep the
annotated output outside Git because it contains the source appearance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile


def inspect(input_path: Path, output_path: Path, mode: str, print_every: int) -> dict:
    import cv2

    if mode != "haar":
        raise SystemExit("Only the production Haar face detector is available.")

    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise SystemExit("Could not open the video.")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise SystemExit("Video metadata is invalid.")

    haar = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
    if haar.empty():
        capture.release()
        raise SystemExit("OpenCV Haar cascade is unavailable.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise SystemExit("Could not create the annotated output video.")

    counts = {"frames": 0, "haar_face_frames": 0}
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            counts["frames"] += 1
            annotated = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            haar_faces = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
            for x, y, box_width, box_height in haar_faces:
                cv2.rectangle(annotated, (x, y), (x + box_width, y + box_height), (0, 255, 0), 3)

            counts["haar_face_frames"] += int(len(haar_faces) > 0)
            writer.write(annotated)

            if counts["frames"] == 1 or counts["frames"] % print_every == 0:
                print(
                    f"frame={counts['frames']:>5} time={counts['frames'] / fps:>7.2f}s "
                    f"haar_faces={len(haar_faces):>2}",
                    flush=True,
                )
    finally:
        capture.release()
        writer.release()

    counts["fps"] = fps
    counts["width"] = width
    counts["height"] = height
    counts["output"] = str(output_path)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Approved local video to inspect")
    parser.add_argument("--output", type=Path, default=Path(tempfile.gettempdir()) / "mds01-vision-check.mp4")
    parser.add_argument("--mode", choices=("haar",), default="haar")
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
