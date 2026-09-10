"""Print aggregate technical inventory without identifiers, names, or paths."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path


def inventory(root: Path) -> dict:
    os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
    import cv2
    cv2.setLogLevel(0)
    formats, rates, resolutions = Counter(), Counter(), Counter()
    readable, invalid, annotations, duration = 0, 0, 0, 0.0
    if not root.is_dir():
        return {"video_count": 0, "error": "Input directory is unavailable."}
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            continue
        suffix = path.suffix.lower()
        if suffix in {".csv", ".json", ".tsv", ".txt"}:
            annotations += 1
        if suffix not in {".mp4", ".mov", ".webm", ".avi", ".mkv"}:
            continue
        formats[suffix] += 1
        cap = cv2.VideoCapture(str(path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            ok, _ = cap.read()
            if not ok or fps <= 0 or count <= 0:
                invalid += 1
                continue
            readable += 1
            duration += count / fps
            rates[str(round(fps, 3))] += 1
            resolutions[f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"] += 1
        finally:
            cap.release()
    return {"video_count": sum(formats.values()), "readable_count": readable,
            "unreadable_count": invalid, "formats": dict(formats), "fps_counts": dict(rates),
            "resolution_counts": dict(resolutions), "total_duration_seconds": round(duration, 2),
            "possible_annotation_file_count": annotations,
            "annotations_validated": False, "supported_upload_formats": [".mp4", ".mov", ".webm"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = inventory(args.directory)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result.get("readable_count", 0) else 2)
