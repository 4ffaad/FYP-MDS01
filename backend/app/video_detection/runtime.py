"""CPU VSViG runner using hash-checked upstream sources and pose weights.

Runs in a separate process to isolate upstream imports from the web/EEG runtime.
No checkpoint, source code, or patient data is downloaded here.
"""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from backend.app.video_detection.contract import DetectionError, load_contract, validate_predictions
from backend.app.video_detection.visualization import render_visualization


def _patch_occlusion_evidence(model, patches, coordinates, score, patch_labels):
    """Measure bounded model sensitivity to each anonymous VSViG input patch."""

    import torch

    parts = []
    with torch.inference_mode():
        for patch_index in range(patches.shape[2]):
            occluded = patches.clone()
            occluded[:, :, patch_index] = 0
            alternate = model(occluded, coordinates)
            if alternate.numel() != 1:
                raise DetectionError("invalid_model_output")
            parts.append({
                "patch_index": patch_index,
                "component": patch_labels[patch_index],
                "score_change": float(score - alternate.item()),
            })
    return {
        "method": "patch-occlusion",
        "note": "Research sensitivity: each anonymous model input patch was replaced with neutral pixels. This is not a clinical explanation.",
        "patches": sorted(parts, key=lambda item: abs(item["score_change"]), reverse=True),
    }


def _track_single_pose(previous_poses, keypoints, pose_class, track_function):
    """Require the pinned OpenPose tracker to preserve one subject identity."""

    current_pose = pose_class(keypoints[:, :2].copy(), float(keypoints[:, 2].mean()))
    current_poses = [current_pose]
    track_function(previous_poses, current_poses, threshold=3, smooth=False)
    if previous_poses and current_pose.id != previous_poses[0].id:
        raise DetectionError("ambiguous_or_missing_pose")
    return current_poses


def module_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load upstream module: {name}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return module


def run(source: Path, visualization_output: Path | None = None) -> dict:
    root, contract = load_contract()
    import cv2
    import numpy as np
    import torch

    torch.set_num_threads(2)
    sys.path.insert(0, str(root / "openpose"))
    from demo import infer_fast
    from models.with_mobilenet import PoseEstimationWithMobileNet
    from modules.keypoints import extract_keypoints, group_keypoints
    from modules.pose import Pose, track_poses

    upstream = module_from_file("mds01_vsvig_upstream", root / "vsvig/VSViG.py")
    patches_module = module_from_file("mds01_vsvig_patches", root / "vsvig/extract_patches.py")
    partitions = torch.load(root / "dy_point_order.pt", map_location="cpu", weights_only=True)
    model = upstream.STViG(SimpleNamespace(
        dynamic=1, num_layer=[2, 2, 6, 2], output_channels=[24, 48, 96, 192],
        dynamic_point_order=partitions, expansion=2, pos_emb="stem",
    ))
    model.load_state_dict(torch.load(root / "VSViG-base.pth", map_location="cpu", weights_only=True), strict=True)
    model.eval()
    pose = PoseEstimationWithMobileNet()
    checkpoint = torch.load(root / "pose.pth", map_location="cpu", weights_only=True)
    pose.load_state_dict(checkpoint.get("state_dict", checkpoint), strict=True)
    pose.eval()

    p = contract["preprocessing"]
    capture = cv2.VideoCapture(str(source))
    fps = capture.get(cv2.CAP_PROP_FPS)
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if (not capture.isOpened() or fps < p["sample_fps"] or count <= 0
        or int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) != p["width"]
        or int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) != p["height"]):
        capture.release()
        raise DetectionError("video_incompatible")
    duration = count / fps
    patches, coordinates, times, rows = [], [], [], []
    pose_samples = []
    previous_poses = []
    strongest_flagged = None
    frame_index, next_sample = 0, 0
    # The upstream extractor removes slots 1, 14, and 15. Place the reviewed
    # 15-point model order into its surviving slots before calling it.
    kept = [i for i in range(18) if i not in (1, 14, 15)]
    try:
        with torch.inference_mode():
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                index = frame_index
                frame_index += 1
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if abs(timestamp - index / fps) > max(0.05, 1 / fps):
                    raise DetectionError("video_incompatible")
                if index < round(next_sample * fps / p["sample_fps"]):
                    continue
                next_sample += 1
                heatmaps, pafs, scale, pad = infer_fast(pose, frame, int(p["pose_height"]), 8, 4, True)
                by_type, total = [], 0
                for k in range(18):
                    total += extract_keypoints(heatmaps[:, :, k], by_type, total)
                entries, points = group_keypoints(by_type, pafs)
                # A single visible person is the v1 ceiling. Never choose a
                # clinician/bystander automatically when multiple people appear.
                if len(entries) != 1:
                    raise DetectionError("ambiguous_or_missing_pose")
                keypoints = np.zeros((18, 3), dtype=np.float32)
                for k, point_id in enumerate(entries[0][:18]):
                    if point_id < 0:
                        raise DetectionError("incomplete_pose")
                    point = points[int(point_id)]
                    keypoints[k] = ((point[0] * 2 - pad[1]) / scale, (point[1] * 2 - pad[0]) / scale, point[2])
                if (keypoints[:, 2] < p["min_keypoint_score"]).any():
                    raise DetectionError("incomplete_pose")
                if (keypoints[:, :2] < 0).any() or (keypoints[:, 0] >= frame.shape[1]).any() or (keypoints[:, 1] >= frame.shape[0]).any():
                    raise DetectionError("incomplete_pose")
                previous_poses = _track_single_pose(
                    previous_poses,
                    keypoints,
                    Pose,
                    track_poses,
                )
                pose_samples.append((index / fps, keypoints.copy()))
                reordered = keypoints.copy()
                reordered[kept] = keypoints[p["patch_order"]]
                if p["color_order"] == "RGB":
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                patch = patches_module.extract_patches(
                    frame,
                    reordered,
                    kernel_size=int(p["patch_kernel_size"]),
                    kernel_sigma=float(p["patch_sigma"]),
                    scale=float(p["patch_scale"]),
                )
                patch_shape = (15, 32, 32, 3)
                if patch.shape != patch_shape or not np.isfinite(patch).all():
                    raise DetectionError("invalid_patch")
                kpts = keypoints[p["keypoint_order"]].copy()
                kpts[:, :2] *= p["coordinate_scale"]
                patches.append(patch.transpose(0, 3, 1, 2).astype(np.float32) * p["pixel_scale"])
                coordinates.append(kpts)
                times.append(index / fps)
                if len(patches) == p["frames"]:
                    tensor = torch.from_numpy(np.stack(patches)[None])
                    k_tensor = torch.from_numpy(np.stack(coordinates)[None])
                    result = model(tensor, k_tensor)
                    if result.numel() != 1:
                        raise DetectionError("invalid_model_output")
                    score = result.item()
                    rows.append({"start_time": times[0], "end_time": min(duration, times[-1] + 1 / p["sample_fps"]), "raw_score": score})
                    if score >= contract["threshold"] and (strongest_flagged is None or score > strongest_flagged[0]):
                        strongest_flagged = (score, len(rows) - 1, tensor, k_tensor)
                    step = p["stride_frames"]
                    del patches[:step], coordinates[:step], times[:step]
    finally:
        capture.release()
    if frame_index != count:
        raise DetectionError("truncated_video")
    metadata = {
        "model_name": "VSViG-base", "model_version": contract["upstream_commit"],
        "weights_hash": contract["sha256"]["VSViG-base.pth"],
        "pose_weights_hash": contract["sha256"]["pose.pth"],
        "partition_hash": contract["sha256"]["dy_point_order.pt"],
        "preprocessing_version": p["version"], "contract_version": contract["version"],
        "threshold": contract["threshold"], "calibrated": False,
        "window_frames": p["frames"], "sample_fps": p["sample_fps"], "stride_frames": p["stride_frames"],
        "input_resolution": {"width": p["width"], "height": p["height"]},
        "patch_labels": p["patch_labels"],
        "source_repository": contract.get("upstream_repository"),
        "pose_repository": contract.get("pose_repository"),
        "pose_model": "Lightweight OpenPose",
        "privacy_input": "full-frame-blurred video; audio is not decoded by the model",
        "postprocessing": "per-window threshold; score is not calibrated",
    }
    if strongest_flagged is not None:
        score, row_index, tensor, k_tensor = strongest_flagged
        rows[row_index]["model_evidence"] = _patch_occlusion_evidence(
            model, tensor, k_tensor, score, p["patch_labels"]
        )
    result = validate_predictions(rows, duration, metadata)
    result["duration_seconds"] = frame_index / fps
    result["fps"] = fps
    result["frame_count"] = frame_index
    if visualization_output is not None:
        result["visualization"] = render_visualization(
            source,
            visualization_output,
            pose_samples,
        )
    else:
        result["visualization"] = {
            "available": False,
            "media_type": "video/mp4",
            "audio_included": False,
            "privacy_method": "full-frame-blur-and-skeleton-overlay",
            "overlay": {"skeleton": True, "model_score": False, "event_markers": False},
            "frontend_overlay": {"model_score": True, "event_markers": True},
        }
    return result


if __name__ == "__main__":
    try:
        visualization_output = None
        if len(sys.argv) == 4:
            visualization_output = Path(sys.argv[3])
        elif len(sys.argv) != 3:
            raise DetectionError("runtime_incompatible")
        result = run(Path(sys.argv[1]), visualization_output)
        Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))
    except DetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except Exception:
        # Upstream exceptions can include private paths; never forward them.
        print("runtime_incompatible", file=sys.stderr)
        sys.exit(2)
