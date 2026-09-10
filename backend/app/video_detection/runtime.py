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


def module_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(source: Path) -> dict:
    root, contract = load_contract()
    import cv2
    import numpy as np
    import torch

    torch.set_num_threads(2)
    sys.path.insert(0, str(root / "openpose"))
    from demo import infer_fast
    from models.with_mobilenet import PoseEstimationWithMobileNet
    from modules.keypoints import extract_keypoints, group_keypoints

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
    frame_index, next_sample = 0, 0
    # Upstream extractor drops neck and two eye points. Explicitly reorder its
    # input so the reviewed patch order is preserved independently of pose order.
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
                reordered = keypoints.copy()
                reordered[kept] = keypoints[p["patch_order"]]
                if p["color_order"] == "RGB":
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                patch = patches_module.extract_patches(frame, reordered)
                if patch.shape != (15, 32, 32, 3) or not np.isfinite(patch).all():
                    raise DetectionError("invalid_patch")
                kpts = keypoints[p["keypoint_order"]].copy()
                kpts[:, :2] *= p["coordinate_scale"]
                patches.append(patch.transpose(0, 3, 1, 2).astype(np.float32) * p["pixel_scale"])
                coordinates.append(kpts)
                times.append(index / fps)
                if len(patches) == 30:
                    tensor = torch.from_numpy(np.stack(patches)[None])
                    k_tensor = torch.from_numpy(np.stack(coordinates)[None])
                    result = model(tensor, k_tensor)
                    if result.numel() != 1:
                        raise DetectionError("invalid_model_output")
                    rows.append({"start_time": times[0], "end_time": min(duration, times[-1] + 1 / p["sample_fps"]), "raw_score": result.item()})
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
        "window_frames": 30, "sample_fps": p["sample_fps"], "stride_frames": p["stride_frames"],
    }
    return validate_predictions(rows, duration, metadata)


if __name__ == "__main__":
    try:
        result = run(Path(sys.argv[1]))
        Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))
    except DetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except Exception:
        # Upstream exceptions can include private paths; never forward them.
        print("runtime_incompatible", file=sys.stderr)
        sys.exit(2)
