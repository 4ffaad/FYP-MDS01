"""Emit an UNREVIEWED external asset manifest. Hashes do not imply review."""

import argparse
import json
from pathlib import Path

from backend.app.video_detection.contract import UPSTREAM_COMMIT, digest


def template(root: Path) -> dict:
    names = {"VSViG-base.pth", "pose.pth", "dy_point_order.pt"}
    names.update(str(p.relative_to(root)) for folder in ("vsvig", "openpose") for p in (root / folder).rglob("*.py"))
    return {
        "reviewed": False, "review_reference": None, "version": None,
        "upstream_commit": UPSTREAM_COMMIT,
        "sha256": {name: digest(root / name) if (root / name).is_file() else None for name in sorted(names)},
        "threshold": 0.5,
        "preprocessing": {
            "version": None, "frames": 30, "stride_frames": None, "sample_fps": None,
            "width": None, "height": None, "pose_height": None,
            "patch_order": None, "keypoint_order": None, "third_feature": None,
            "pixel_scale": None, "coordinate_scale": None, "color_order": None,
            "min_keypoint_score": None,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(template(args.directory), indent=2))
