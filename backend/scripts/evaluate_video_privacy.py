"""Measure VSViG utility before and after face redaction on approved labelled video."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.research.evaluation import write_report
from backend.app.research.video_privacy_evaluation import evaluate_video_privacy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("video-privacy-evaluation.json"))
    args = parser.parse_args()
    report = evaluate_video_privacy(args.dataset_root, args.manifest, split=args.split, seed=args.seed)
    write_report(report, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
