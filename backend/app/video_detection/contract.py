"""Validate externally mounted, explicitly reviewed VSViG assets before use."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat

UPSTREAM_REPOSITORY = "https://github.com/xuyankun/VSViG"
UPSTREAM_COMMIT = "1026e7e7f2287b96f3cc375830f2836ffdf4588e"
POSE_REPOSITORY = "https://github.com/Daniil-Osokin/lightweight-human-pose-estimation.pytorch"
POSE_COMMIT = "d23c284b09acf27a163e1febd511e7482cac25ed"
UPSTREAM_SOURCES = {
    "vsvig/VSViG.py": "54fc961308e92bef553a69f2ca08cc4897827ab3f429c0884393544027ce4284",
    "vsvig/extract_patches.py": "f3ea57aff34096b475f06e19d82d823bd9d345ee93efdcc869361295062ce479",
}
UPSTREAM_ARTIFACTS = {
    "VSViG-base.pth": "0a95e3e0093730dc535e21a84f04943c73549a2b6a19a85e33aebc7c64f965a9",
    "pose.pth": "7c61f38c17d4b54d7f429717544be1de0905f901aa6f7913f7868ae5c5b83827",
    "dy_point_order.pt": "9aa778ca1221f47b6afe0242787becfdfaae3f2424b54dd15a48c585ef0a0ced",
}
POSE_SOURCES = {
    "openpose/demo.py": "12a9fe4492f762ca76ed5774e0f459a9434dd63f26c8bd40379956355f129921",
    "openpose/val.py": "4a57a8d4e70e044888219e538db29d4f0c519430c32fccb194eab72c2b4b5412",
    "openpose/datasets/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "openpose/datasets/coco.py": "50aa2024aa2bc1eba34a6a22b514b2cacf127fb5afdfb799c027bc134335295a",
    "openpose/datasets/transformations.py": "7f9abcad8724ba2fe360e14b751efd852740522b1ceb02805b68a95fd865d1a0",
    "openpose/models/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "openpose/models/with_mobilenet.py": "28fe334f17fd0a78533ed8572762085bbd17741126d938718fb518367a2dc1ed",
    "openpose/modules/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "openpose/modules/conv.py": "919d70cc157fdf05ecc3f3380e40d1e153949035101ad85ebbbd4bf051193b4f",
    "openpose/modules/keypoints.py": "78a2cd7a2def2f843e3ca85b803952cbf25a04b54ed85a64ab1b6312f9cf7376",
    "openpose/modules/load_state.py": "bdc8680083007a209c534674701e11bfe074f424c7b8910fd3f63ac77ce5ab20",
    "openpose/modules/one_euro_filter.py": "c838b216a731b50405c5c9b10596cfec92b6e6f10c3e23bb4da2ed1640623f23",
    "openpose/modules/pose.py": "bf8fcd1a898c1bae2cfd1b56330a1375865a61ab70186a64465b595179792eae",
}
LICENSES = {
    "vsvig/LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "openpose/LICENSE": "61a7b068237f7262b2abbef47f2a7a79e8b1df18083db8a75abfe8ec1b2b0a36",
}
REVIEWED_CONTRACT_SHA256 = "e55484a3c9d6eb6ef5559970eae5c6eab7a0c2d3d002340486676fc052512429"

DEFAULT_PATCH_ORDER = [0, 15, 14, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
DEFAULT_PATCH_LABELS = [
    "nose",
    "left eye",
    "right eye",
    "right shoulder",
    "right elbow",
    "right wrist",
    "left shoulder",
    "left elbow",
    "left wrist",
    "right hip",
    "right knee",
    "right ankle",
    "left hip",
    "left knee",
    "left ankle",
]
DEFAULT_PREPROCESSING = {
    "version": "mds01-vsvig-technical-1",
    "frames": 30,
    "stride_frames": 3,
    "sample_fps": 6.0,
    "width": 1920,
    "height": 1080,
    "pose_height": 256,
    "patch_kernel_size": 128,
    "patch_sigma": 0.3,
    "patch_scale": 0.25,
    "patch_order": DEFAULT_PATCH_ORDER,
    "keypoint_order": DEFAULT_PATCH_ORDER,
    "patch_labels": DEFAULT_PATCH_LABELS,
    "third_feature": "confidence",
    "pixel_scale": 1.0,
    "coordinate_scale": 1.0,
    "color_order": "BGR",
    # OpenPose suppresses heatmap candidates below 0.1; this adapter keeps the
    # same lower bound while still requiring a complete single-person pose.
    "min_keypoint_score": 0.1,
}
DEFAULT_THRESHOLD = 0.5


class DetectionError(RuntimeError):
    """Only fixed public error codes cross the API boundary."""


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _strict_file(root: Path, relative: str) -> Path:
    """Return a regular, non-symlinked file beneath an asset root."""

    if (
        not isinstance(relative, str)
        or not relative
        or relative.startswith(("/", "\\"))
        or any(part in {"", ".", ".."} for part in relative.replace("\\", "/").split("/"))
    ):
        raise DetectionError("asset_mismatch")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise DetectionError("asset_mismatch")
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        raise
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise DetectionError("asset_mismatch")
    current = root
    for index, part in enumerate(parts):
        current /= part
        entry_stat = current.lstat()
        if stat.S_ISLNK(entry_stat.st_mode):
            raise DetectionError("asset_mismatch")
        if index < len(parts) - 1:
            if not stat.S_ISDIR(entry_stat.st_mode):
                raise DetectionError("asset_mismatch")
        elif not stat.S_ISREG(entry_stat.st_mode):
            raise DetectionError("asset_mismatch")
    return current


def _bundle_layout(root: Path) -> tuple[set[str], set[str]]:
    """Return regular-file and directory entries without following links."""

    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        raise
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise DetectionError("asset_mismatch")
    files: set[str] = set()
    directories: set[str] = set()
    for current, names, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in names:
            path = current_path / name
            entry_stat = path.lstat()
            if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISDIR(entry_stat.st_mode):
                raise DetectionError("asset_mismatch")
            directories.add(str(path.relative_to(root).as_posix()))
        for name in filenames:
            path = current_path / name
            entry_stat = path.lstat()
            if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISREG(entry_stat.st_mode):
                raise DetectionError("asset_mismatch")
            files.add(str(path.relative_to(root).as_posix()))
    return files, directories


def load_contract(root: Path | None = None) -> tuple[Path, dict]:
    root = Path(os.path.abspath((root or Path(os.environ.get("VSVIG_ASSET_DIR", "/opt/vsvig"))).expanduser()))
    try:
        contract_path = _strict_file(root, "contract.json")
        expected_contract_hash = os.environ.get("VSVIG_CONTRACT_SHA256", "").lower()
        actual_contract_hash = digest(contract_path)
        if (
            len(expected_contract_hash) != 64
            or actual_contract_hash != expected_contract_hash
            or actual_contract_hash != REVIEWED_CONTRACT_SHA256
        ):
            raise DetectionError("contract_unreviewed")
        contract = json.loads(contract_path.read_text())
        if not isinstance(contract, dict):
            raise DetectionError("contract_invalid")
        if contract.get("reviewed") is not True:
            raise DetectionError("contract_unreviewed")
        if contract.get("upstream_commit") != UPSTREAM_COMMIT:
            raise DetectionError("asset_mismatch")
        if (
            contract.get("upstream_repository") != UPSTREAM_REPOSITORY
            or contract.get("pose_repository") != POSE_REPOSITORY
            or contract.get("pose_commit") != POSE_COMMIT
        ):
            raise DetectionError("asset_mismatch")
        hashes = contract["sha256"]
        if not isinstance(hashes, dict):
            raise DetectionError("contract_invalid")
        expected_hashes = {**UPSTREAM_SOURCES, **UPSTREAM_ARTIFACTS, **POSE_SOURCES, **LICENSES}
        if set(hashes) != set(expected_hashes):
            raise DetectionError("asset_mismatch")
        if any(hashes.get(name) != expected for name, expected in expected_hashes.items()):
            raise DetectionError("asset_mismatch")
        expected_files = set(expected_hashes) | {"contract.json"}
        expected_directories = {
            str(parent.as_posix())
            for name in expected_files
            for parent in Path(name).parents
            if str(parent) != "."
        }
        files, directories = _bundle_layout(root)
        if files != expected_files or directories != expected_directories:
            raise DetectionError("asset_mismatch")
        for name, expected in hashes.items():
            if not isinstance(expected, str) or len(expected) != 64:
                raise DetectionError("asset_mismatch")
            path = _strict_file(root, name)
            if digest(path) != expected:
                raise DetectionError("asset_mismatch")
        p = contract["preprocessing"]
        if not isinstance(p, dict):
            raise DetectionError("contract_invalid")
        if (
            contract.get("version") != "mds01-vsvig-technical-1"
            or not contract["review_reference"]
            or p.get("version") != DEFAULT_PREPROCESSING["version"]
        ):
            raise DetectionError("contract_unreviewed")
        if set(p) != set(DEFAULT_PREPROCESSING) or any(
            p[key] != value for key, value in DEFAULT_PREPROCESSING.items()
        ):
            raise DetectionError("contract_invalid")
        for key in (
            "sample_fps",
            "pixel_scale",
            "coordinate_scale",
            "pose_height",
            "width",
            "height",
            "patch_sigma",
            "patch_scale",
        ):
            if isinstance(p[key], bool) or not math.isfinite(p[key]) or p[key] <= 0:
                raise DetectionError("contract_invalid")
        if (
            p["frames"] != 30
            or type(p["stride_frames"]) is not int
            or not 1 <= p["stride_frames"] <= 30
            or type(p["patch_kernel_size"]) is not int
            or p["patch_kernel_size"] != 128
            or math.ceil(p["patch_kernel_size"] * p["patch_scale"]) != 32
        ):
            raise DetectionError("contract_invalid")
        for key in ("patch_order", "keypoint_order"):
            if (
                type(p[key]) is not list
                or len(p[key]) != 15
                or len(set(p[key])) != 15
                or any(type(i) is not int or not 0 <= i < 18 for i in p[key])
            ):
                raise DetectionError("contract_invalid")
        if (
            p["third_feature"] != "confidence"
            or p["color_order"] not in ("BGR", "RGB")
            or type(p["patch_labels"]) is not list
            or len(p["patch_labels"]) != 15
            or len(set(p["patch_labels"])) != 15
            or any(not isinstance(label, str) or not label for label in p["patch_labels"])
        ):
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
    """Reject invalid runtime outputs and build review-friendly timeline data."""
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
            patch_labels = model.get("patch_labels") if isinstance(model, dict) else None
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
                    or (
                        isinstance(patch_labels, list)
                        and len(patch_labels) == 15
                        and item.get("component") != patch_labels[item["patch_index"]]
                    )
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

    timeline = [
        {
            "timestamp": (window["start_time"] + window["end_time"]) / 2,
            "start_time": window["start_time"],
            "end_time": window["end_time"],
            "score": window["score"],
            "seizure_detected": window["seizure_detected"],
        }
        for window in windows
    ]
    events = []
    for interval in intervals:
        supporting = [
            window
            for window in windows
            if window["seizure_detected"]
            and window["start_time"] < interval["end_time"]
            and window["end_time"] > interval["start_time"]
        ]
        peak = max(supporting, key=lambda window: window["score"])
        events.append(
            {
                "start_time": interval["start_time"],
                "end_time": interval["end_time"],
                "peak_score": peak["score"],
                "peak_timestamp": (peak["start_time"] + peak["end_time"]) / 2,
            }
        )
    summary = {
        "peak_score": max(window["score"] for window in windows),
        "potential_event_detected": bool(events),
        "event_count": len(events),
        "threshold": model["threshold"],
    }
    return {
        "model": model,
        "predictions": windows,
        "timeline": timeline,
        "intervals": intervals,
        "events": events,
        "summary": summary,
        "recording_probability_available": False,
    }
