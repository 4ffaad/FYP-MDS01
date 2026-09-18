"""Emit a VSViG asset manifest; source hashes do not imply clinical validity."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.video_detection.contract import (
    DEFAULT_PREPROCESSING,
    DEFAULT_THRESHOLD,
    LICENSES,
    POSE_COMMIT,
    POSE_REPOSITORY,
    POSE_SOURCES,
    UPSTREAM_ARTIFACTS,
    UPSTREAM_COMMIT,
    UPSTREAM_REPOSITORY,
    UPSTREAM_SOURCES,
    digest,
)


def template(root: Path, *, reviewed: bool = False) -> dict:
    names = set(UPSTREAM_ARTIFACTS) | set(UPSTREAM_SOURCES) | set(POSE_SOURCES) | set(LICENSES)
    names.update(
        str(p.relative_to(root))
        for folder in ("vsvig", "openpose")
        for p in (root / folder).rglob("*.py")
    )
    return {
        "reviewed": reviewed,
        "review_scope": "technical-source-and-runtime-choice" if reviewed else None,
        "review_reference": (
            "MDS01 technical review of the pinned VSViG assets and Lightweight OpenPose "
            "adapter choices; not clinical validation."
            if reviewed
            else None
        ),
        "version": "mds01-vsvig-technical-1" if reviewed else None,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "pose_repository": POSE_REPOSITORY,
        "pose_commit": POSE_COMMIT,
        "sha256": {
            name: digest(root / name) if (root / name).is_file() else None
            for name in sorted(names)
        },
        "threshold": DEFAULT_THRESHOLD,
        "preprocessing": deepcopy(DEFAULT_PREPROCESSING),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--reviewed",
        action="store_true",
        help="mark the source/runtime contract reviewed; this is not clinical validation",
    )
    args = parser.parse_args()
    print(json.dumps(template(args.directory, reviewed=args.reviewed), indent=2))
