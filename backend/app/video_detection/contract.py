"""Validate externally mounted, explicitly reviewed VSViG assets before use."""

import hashlib
import json
import math
import os
from pathlib import Path

UPSTREAM_COMMIT = "1026e7e7f2287b96f3cc375830f2836ffdf4588e"
UPSTREAM_SOURCES = {
    "vsvig/VSViG.py": "54fc961308e92bef553a69f2ca08cc4897827ab3f429c0884393544027ce4284",
    "vsvig/extract_patches.py": "f3ea57aff34096b475f06e19d82d823bd9d345ee93efdcc869361295062ce479",
}


class DetectionError(RuntimeError):
    """Only fixed public error codes cross the API boundary."""


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_contract(root: Path | None = None) -> tuple[Path, dict]:
    root = root or Path(os.environ.get("VSVIG_ASSET_DIR", "/opt/vsvig"))
    try:
        contract_path = root / "contract.json"
        if not contract_path.is_file():
            raise DetectionError("assets_missing")
        expected_contract_hash = os.environ.get("VSVIG_CONTRACT_SHA256", "")
        if len(expected_contract_hash) != 64 or digest(contract_path) != expected_contract_hash:
            raise DetectionError("contract_unreviewed")
        contract = json.loads(contract_path.read_text())
        if contract.get("reviewed") is not True:
            raise DetectionError("contract_unreviewed")
        if contract["upstream_commit"] != UPSTREAM_COMMIT:
            raise DetectionError("asset_mismatch")
        required = {"vsvig/VSViG.py", "vsvig/extract_patches.py", "VSViG-base.pth", "pose.pth", "dy_point_order.pt"}
        hashes = contract["sha256"]
        if any(hashes.get(name) != expected for name, expected in UPSTREAM_SOURCES.items()):
            raise DetectionError("asset_mismatch")
        source_files = {str(p.relative_to(root)) for folder in ("vsvig", "openpose") for p in (root / folder).rglob("*.py")}
        if not source_files or not (required | source_files).issubset(hashes):
            raise DetectionError("asset_mismatch")
        for name, expected in hashes.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not isinstance(expected, str) or len(expected) != 64 or digest(path) != expected:
                raise DetectionError("asset_mismatch")
        p = contract["preprocessing"]
        if not contract["version"] or not contract["review_reference"] or not p["version"]:
            raise DetectionError("contract_unreviewed")
        for key in ("sample_fps", "pixel_scale", "coordinate_scale", "pose_height", "width", "height"):
            if isinstance(p[key], bool) or not math.isfinite(p[key]) or p[key] <= 0:
                raise DetectionError("contract_invalid")
        if p["frames"] != 30 or type(p["stride_frames"]) is not int or not 1 <= p["stride_frames"] <= 30:
            raise DetectionError("contract_invalid")
        for key in ("patch_order", "keypoint_order"):
            if len(p[key]) != 15 or len(set(p[key])) != 15 or any(type(i) is not int or not 0 <= i < 18 for i in p[key]):
                raise DetectionError("contract_invalid")
        if p["third_feature"] != "confidence" or p["color_order"] not in ("BGR", "RGB"):
            raise DetectionError("contract_invalid")
        if not 0 <= p["min_keypoint_score"] <= 1 or not 0 < contract["threshold"] < 1:
            raise DetectionError("contract_invalid")
        return root, contract
    except DetectionError:
        raise
    except FileNotFoundError as exc:
        raise DetectionError("assets_missing") from exc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DetectionError("contract_invalid") from exc


def validate_predictions(rows: list, duration: float, model: dict) -> dict:
    """Reject invalid runtime outputs and merge overlapping positive supports."""
    if not rows or not math.isfinite(duration) or duration <= 0:
        raise DetectionError("no_usable_windows")
    windows, intervals = [], []
    previous = -1.0
    for row in rows:
        start, end, score = (float(row[k]) for k in ("start_time", "end_time", "raw_score"))
        if not all(math.isfinite(v) for v in (start, end, score)) or not 0 <= start < end <= duration + 1e-3 or start <= previous or not 0 <= score <= 1:
            raise DetectionError("invalid_model_output")
        previous = start
        flagged = score >= model["threshold"]
        window = {"start_time": start, "end_time": end, "raw_score": score, "score": score,
                  "score_type": "uncalibrated_model_score", "seizure_detected": flagged, **model}
        evidence = row.get("model_evidence")
        if evidence is not None:
            patches = evidence.get("patches") if isinstance(evidence, dict) else None
            if (
                not isinstance(evidence, dict)
                or evidence.get("method") != "patch-occlusion"
                or not isinstance(patches, list)
                or len(patches) != 15
                or {item.get("patch_index") for item in patches if isinstance(item, dict)} != set(range(15))
                or any(
                    not isinstance(item, dict)
                    or type(item.get("patch_index")) is not int
                    or not 0 <= item["patch_index"] < 15
                    or not math.isfinite(float(item.get("score_change", float("nan"))))
                    for item in patches
                )
            ):
                raise DetectionError("invalid_model_output")
            window["model_evidence"] = evidence
        windows.append(window)
        if flagged:
            if intervals and start <= intervals[-1]["end_time"]:
                intervals[-1]["end_time"] = max(end, intervals[-1]["end_time"])
            else:
                intervals.append({"start_time": start, "end_time": end})
    return {"model": model, "predictions": windows, "intervals": intervals,
            "recording_probability_available": False}
