"""Fit one CHB-MIT temperature calibrator for one privacy profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.app.privacy.methods import CANONICAL_COMBINED, METADATA_SCRUB
from backend.app.research.calibration import fit_temperature, temperature_scale
from backend.app.research.evaluation import collect_evaluation_data
from backend.app.research.metrics import calibration_metrics


def build_calibration_report(data: dict[str, Any]) -> dict[str, Any]:
    """Fit and report one profile without exposing recording paths or samples."""

    labels = data["labels"]
    raw_scores = data["raw_scores"]
    temperature = fit_temperature(labels, raw_scores)
    calibrated_scores = temperature_scale(raw_scores, temperature).tolist()
    return {
        "dataset": data["dataset"],
        "split": data["split"],
        "subjects": data["subjects"],
        "privacy_method": data["privacy_method"],
        "model": data["model"],
        "split_policy": "patient-disjoint fixed chb01-chb10 manifest; windows never split independently",
        "recording_count": data["recording_count"],
        "window_count": data["window_count"],
        "positive_windows": data["positive_windows"],
        "method": "temperature_scaling",
        "temperature": temperature,
        "metrics_before": calibration_metrics(labels, raw_scores),
        "metrics_after": calibration_metrics(labels, calibrated_scores),
        "exclusions": data["exclusions"],
    }


def calibration_profile(report: dict[str, Any], *, status: str) -> dict[str, Any]:
    """Return the contract-safe profile payload from a calibration report."""

    return {
        "status": status,
        "method": report["method"],
        "temperature": report["temperature"],
        "version": "temperature-scaling-v1",
        "dataset": report["dataset"],
        "subjects": report["subjects"],
        "metrics": report["metrics_after"],
    }


def write_contract(
    contract_path: Path,
    privacy_method: str,
    profile: dict[str, Any],
    *,
    activate: bool,
) -> None:
    """Persist one profile and optionally activate both reviewed profiles."""

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    profiles = contract.setdefault("calibration_profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("The model contract calibration_profiles value must be an object.")
    profiles[privacy_method] = profile
    if activate:
        required = (METADATA_SCRUB, CANONICAL_COMBINED)
        if any(name not in profiles for name in required):
            raise ValueError("Both privacy profiles must be fitted before calibration can be activated.")
        for name in required:
            if not isinstance(profiles[name], dict) or profiles[name].get("status") not in {"candidate", "active"}:
                raise ValueError(f"Calibration profile {name} is not a valid candidate.")
            profiles[name]["status"] = "active"
        contract["score_type"] = "calibrated_probability"
        contract["calibration_method"] = "temperature_scaling"
        contract["calibration_status"] = "active"
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    """Fit one profile, write its aggregate report, and optionally update the contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path, help="Directory containing CHB-MIT EDF files.")
    parser.add_argument(
        "--privacy-method",
        choices=(METADATA_SCRUB, CANONICAL_COMBINED),
        required=True,
        help="Privacy profile being calibrated; run once for each profile.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Aggregate calibration report JSON path.")
    parser.add_argument("--write-contract", type=Path, help="Explicitly update this model contract with the fitted profile.")
    parser.add_argument("--activate", action="store_true", help="Activate calibrated inference after both profiles exist.")
    args = parser.parse_args()
    if args.activate and args.write_contract is None:
        parser.error("--activate requires --write-contract.")

    data = collect_evaluation_data(
        dataset_root=args.dataset_root,
        privacy_method=args.privacy_method,
        split="calibration",
    )
    report = build_calibration_report(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_contract:
        write_contract(
            args.write_contract,
            args.privacy_method,
            calibration_profile(report, status="candidate"),
            activate=args.activate,
        )
    print(f"Wrote {args.output}")
    print(f"Temperature: {report['temperature']:.6f}")
    print(f"Brier score: {report['metrics_after']['brier_score']:.6f}")
    print(f"ECE: {report['metrics_after']['expected_calibration_error']:.6f}")
    print(f"NLL: {report['metrics_after']['negative_log_likelihood']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
