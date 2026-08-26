"""Run the patient-disjoint CHB-MIT seizure utility evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.research.evaluation import evaluate_dataset, write_plots, write_report


def main() -> int:
    """Parse evaluation options, run the report, and write JSON output."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path, help="Directory containing the CHB-MIT EDF files.")
    parser.add_argument(
        "--privacy-method",
        choices=("metadata-scrub", "metadata-scrub+signal-obfuscation"),
        default="metadata-scrub",
        help="Privacy profile to evaluate; run the command once for each profile.",
    )
    parser.add_argument("--split", choices=("train", "calibration", "test"), default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("evaluation-report.json"))
    parser.add_argument(
        "--plots",
        type=Path,
        help="Optional PNG path for aggregate confusion/ROC/PR/calibration plots.",
    )
    args = parser.parse_args()

    report = evaluate_dataset(
        dataset_root=args.dataset_root,
        privacy_method=args.privacy_method,
        split=args.split,
        seed=args.seed,
    )
    write_report(report, args.output)
    if args.plots:
        write_plots(report, args.plots)
    print(f"Wrote {args.output}")
    print(f"Evaluated {report['recording_count']} recordings and {report['window_count']} windows.")
    print(f"Accuracy: {report['metrics']['classification']['accuracy']:.4f}")
    print(f"F1: {report['metrics']['classification']['f1']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
