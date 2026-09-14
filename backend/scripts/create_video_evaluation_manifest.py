"""Create an external, patient-disjoint video evaluation manifest from labelled folders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import subprocess


SUBJECT = re.compile(r"^(S\d+)_", re.IGNORECASE)


def subject_id(path: Path) -> str:
    match = SUBJECT.match(path.name)
    if not match:
        raise ValueError("Each video filename must start with a stable S<number> subject ID.")
    return match.group(1).upper()


def split_by_subject(subjects: set[str], seed: int) -> dict[str, str]:
    """Assign every subject to exactly one reproducible 60/20/20 split."""

    ordered = sorted(subjects)
    if len(ordered) < 3:
        raise ValueError("At least three subjects are needed for train/calibration/test splits.")
    random.Random(seed).shuffle(ordered)
    train_end = max(1, round(len(ordered) * 0.6))
    calibration_end = min(len(ordered) - 1, train_end + max(1, round(len(ordered) * 0.2)))
    return {
        subject: "train" if index < train_end else "calibration" if index < calibration_end else "test"
        for index, subject in enumerate(ordered)
    }


def duration_seconds(path: Path) -> float:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    duration = float(completed.stdout.strip())
    if duration <= 0:
        raise ValueError("Video duration must be positive.")
    return duration


def build_manifest(root: Path, seed: int) -> list[dict]:
    files = [(path, path.parent.name.lower()) for path in root.rglob("*.mp4") if path.parent.name.lower() in {"normal", "seizure"}]
    if not files:
        raise ValueError("Expected Normal and Seizure MP4 folders below the dataset root.")
    splits = split_by_subject({subject_id(path) for path, _ in files}, seed)
    entries = []
    for path, label in sorted(files):
        duration = duration_seconds(path)
        entries.append({
            "video": str(path.relative_to(root)),
            "subject_id": subject_id(path),
            "split": splits[subject_id(path)],
            "seizure_intervals": [[0.0, duration]] if label == "seizure" else [],
        })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--seizure-folder-is-fully-positive", action="store_true")
    args = parser.parse_args()
    if not args.seizure_folder_is_fully_positive:
        parser.error("Confirm --seizure-folder-is-fully-positive only when every Seizure clip contains seizure activity for its full duration.")
    args.output.write_text(json.dumps(build_manifest(args.dataset_root.resolve(), args.seed), indent=2) + "\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
