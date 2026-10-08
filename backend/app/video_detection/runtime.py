"""CPU VSViG runner using hash-checked upstream sources and pose weights.

Runs in a separate process to isolate upstream imports from the web/EEG runtime.
No checkpoint, source code, or patient data is downloaded here.
"""

import importlib.util
import importlib.machinery
import json
import math
import os
import platform
from pathlib import Path
import sys
from types import SimpleNamespace

from backend.app.core.config import (
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_MAX_FRAMES,
    VIDEO_MAX_FPS,
    VIDEO_MAX_HEIGHT,
    VIDEO_MAX_WIDTH,
    VIDEO_MIN_FPS,
)
from backend.app.video_detection.contract import DetectionError, load_contract, validate_predictions
from backend.app.video_detection.visualization import render_visualization


def _vsvig_gradcam(model, patches, coordinates, times, threshold):
    """Project graph Grad-CAM relevance onto VSViG's 30 frame × 15 patch nodes."""

    import torch

    activations, logits = [], []
    # Stage 1 is the last VSViG feature block with 15 sampled temporal positions;
    # its graph axis is the same 15 keypoint patches exposed to the reviewer.
    activation_hook = model.backbone[9].register_forward_hook(
        lambda _module, _inputs, output: activations.append(output)
    )
    logit_hook = model.fc[-1].register_forward_hook(
        lambda _module, _inputs, output: logits.append(output)
    )
    try:
        with torch.inference_mode(False), torch.enable_grad():
            patch_input = patches.detach().clone().requires_grad_(True)
            coordinate_input = coordinates.detach().clone()
            result = model(patch_input, coordinate_input)
            if (
                result.numel() != 1
                or not activations
                or not logits
                or activations[-1].ndim != 5
                or activations[-1].shape[0] != 1
                or activations[-1].shape[1] != 15
                or activations[-1].shape[3] != 15
                or logits[-1].numel() != 1
            ):
                raise DetectionError("invalid_model_output")
            score_value = float(result.detach().item())
            target_class = "flagged" if score_value >= threshold else "below_threshold"
            target = logits[-1].sum()
            if target_class == "below_threshold":
                target = -target
            gradients, = torch.autograd.grad(target, activations[-1])
            channel_weights = gradients.mean(dim=(1, 3, 4), keepdim=True)
            cam = torch.relu(
                (channel_weights * activations[-1]).sum(dim=2).squeeze(-1)
            )
            # The selected graph layer has 15 temporal positions. Interpolate its
            # node scores to the 30 source samples used by this model window.
            cam = torch.nn.functional.interpolate(
                cam.transpose(1, 2),
                size=len(times),
                mode="linear",
                align_corners=False,
            ).transpose(1, 2)[0]
            maximum = cam.amax()
            cam = cam / maximum.clamp_min(1e-8)
            if not torch.isfinite(cam).all():
                raise DetectionError("invalid_model_output")
            values = cam.detach().cpu().tolist()
    finally:
        activation_hook.remove()
        logit_hook.remove()

    return {
        "method": "vsvig-graph-grad-cam",
        "target_class": target_class,
        "note": "Gradient-weighted VSViG graph features show relative contribution by sampled time and keypoint patch. Research evidence, not a clinical explanation.",
        "gradcam_samples": [
            {
                "timestamp": round(timestamp, 4),
                "patches": [
                    {
                        "patch_index": patch_index,
                        "relevance": round(float(values[frame_index][patch_index]), 5),
                    }
                    for patch_index in range(15)
                ],
            }
            for frame_index, timestamp in enumerate(times)
        ],
    }


def blur_rgb_patches(patches, strength_percent: int, cv2=None):
    """Blur each extracted 32×32 RGB patch before it reaches VSViG."""

    import numpy as np

    if type(strength_percent) is not int or not 50 <= strength_percent <= 100:
        raise DetectionError("invalid_blur_strength")
    if cv2 is None:
        import cv2
    if (
        not isinstance(patches, np.ndarray)
        or patches.shape != (15, 32, 32, 3)
        or not np.isfinite(patches).all()
    ):
        raise DetectionError("invalid_patch")
    kernel = int(round(3 + 0.28 * strength_percent))
    if kernel % 2 == 0:
        kernel += 1
    kernel = min(kernel, 31)
    return np.stack(
        [cv2.GaussianBlur(patch, (kernel, kernel), sigmaX=0) for patch in patches]
    )


def _validate_required_keypoints(keypoints, indices, width, height, minimum_score):
    """Validate only the landmarks retained by the reviewed 15-point input."""

    if keypoints.shape != (18, 3) or not indices or _missing_required_keypoints(
        keypoints, indices, width, height, minimum_score
    ):
        raise DetectionError("incomplete_pose")


def _last_model_sample_index(sample_count, window_frames, stride_frames):
    """Return the last sample used by any complete strided model window."""

    if sample_count < window_frames:
        return -1
    return (
        ((sample_count - window_frames) // stride_frames) * stride_frames
        + window_frames
        - 1
    )


def _complete_subject_window(rows):
    """Return model-ready samples or the first explicit pose gap reason."""

    if any(row is None or row.get("reason") == "missing_pose" for row in rows):
        return None, "missing_pose"
    if any(row.get("reason") for row in rows):
        return None, next(row["reason"] for row in rows if row.get("reason"))
    return rows, None


def _missing_required_keypoints(keypoints, indices, width, height, minimum_score):
    """Return required landmark indexes that fail the inference gate."""

    import numpy as np

    if keypoints.shape != (18, 3):
        return list(indices)
    points = keypoints[np.asarray(indices, dtype=np.intp)]
    invalid = (
        ~np.isfinite(points).all(axis=1)
        | (points[:, 2] < minimum_score)
        | (points[:, 0] < 0)
        | (points[:, 1] < 0)
        | (points[:, 0] >= width)
        | (points[:, 1] >= height)
    )
    return [int(index) for index, is_invalid in zip(indices, invalid) if is_invalid]


def _keypoints_for_entry(entry, points, scale, pad):
    """Convert one pinned OpenPose group into source-frame COCO coordinates."""

    import numpy as np

    keypoints = np.zeros((18, 3), dtype=np.float32)
    keypoints[:, :2] = -1
    for index, point_id in enumerate(entry[:18]):
        if point_id >= 0:
            point = points[int(point_id)]
            keypoints[index] = (
                (point[0] * 2 - pad[1]) / scale,
                (point[1] * 2 - pad[0]) / scale,
                point[2],
            )
    return keypoints


def _sanitize_keypoints(keypoints, width, height, minimum_score):
    """Keep malformed or low-confidence points out of tracking geometry."""

    import numpy as np

    invalid = (
        ~np.isfinite(keypoints).all(axis=1)
        | (keypoints[:, 2] < minimum_score)
        | (keypoints[:, 0] < 0)
        | (keypoints[:, 1] < 0)
        | (keypoints[:, 0] >= width)
        | (keypoints[:, 1] >= height)
    )
    keypoints[invalid] = (-1, -1, 0)
    return keypoints


def _track_single_pose(previous_poses, keypoints, pose_class, track_function):
    """Require the pinned OpenPose tracker to preserve one subject identity."""

    current_pose = pose_class(keypoints[:, :2].copy(), float(keypoints[:, 2].mean()))
    current_poses = [current_pose]
    track_function(previous_poses, current_poses, threshold=3, smooth=False)
    if previous_poses and current_pose.id != previous_poses[0].id:
        raise DetectionError("ambiguous_or_missing_pose")
    return current_poses


def _adapt_pinned_vsvig_source(source: str) -> str:
    """Use timm's current registry import without changing the verified file."""

    deprecated_import = "from timm.models.registry import register_model"
    current_import = "from timm.models import register_model"
    if source.count(deprecated_import) != 1:
        raise DetectionError("runtime_incompatible")
    return source.replace(deprecated_import, current_import, 1)


def _configure_torch_backend(torch, enabled: bool | None = None) -> None:
    """Disable NNPACK by default only on ARM, where its warning is noisy."""

    if enabled is None:
        configured = os.environ.get("MDS01_NNPACK_ENABLED")
        if configured is None:
            if platform.machine().lower() not in {"aarch64", "arm64"}:
                return
            enabled = False
        else:
            normalized = configured.lower()
            if normalized not in {"true", "false"}:
                raise DetectionError("runtime_incompatible")
            enabled = normalized == "true"
    torch.backends.nnpack.set_flags(enabled)


class _PinnedVSViGSourceLoader(importlib.machinery.SourceFileLoader):
    """Compile the verified upstream source with one import-path update."""

    def get_code(self, fullname):
        source = Path(self.path).read_text(encoding="utf-8")
        adapted = _adapt_pinned_vsvig_source(source)
        return self.source_to_code(adapted, self.path)


def module_from_file(name, path):
    source_path = Path(path)
    if source_path.name == "VSViG.py" and source_path.parent.name == "vsvig":
        loader = _PinnedVSViGSourceLoader(name, str(source_path))
        spec = importlib.util.spec_from_loader(name, loader)
    else:
        spec = importlib.util.spec_from_file_location(name, source_path)
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


def run(
    model_source: Path,
    visualization_output: Path | None = None,
    *,
    pose_source: Path | None = None,
    blur_strength_percent: int = 100,
) -> dict:
    """Run pose on source frames and VSViG on separately blurred RGB patches."""

    root, contract = load_contract()
    import cv2
    import numpy as np
    import torch

    _configure_torch_backend(torch)
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
    required_keypoints = sorted(set(p["keypoint_order"]) | set(p["patch_order"]))
    model_capture = cv2.VideoCapture(str(model_source))
    same_source = pose_source is None or pose_source == model_source
    pose_capture = model_capture if same_source else cv2.VideoCapture(str(pose_source))
    fps = model_capture.get(cv2.CAP_PROP_FPS)
    count = int(model_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(model_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(model_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    pose_fps = pose_capture.get(cv2.CAP_PROP_FPS)
    pose_count = int(pose_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if (
        not model_capture.isOpened()
        or not pose_capture.isOpened()
        or fps < p["sample_fps"]
        or count <= 0
        or (width, height) != (p["width"], p["height"])
        or pose_count != count
        or int(pose_capture.get(cv2.CAP_PROP_FRAME_WIDTH)) != width
        or int(pose_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) != height
        or not math.isclose(pose_fps, fps, rel_tol=0.01, abs_tol=0.01)
    ):
        if pose_capture is not model_capture:
            pose_capture.release()
        model_capture.release()
        raise DetectionError("video_incompatible")
    duration = count / fps
    sample_count = 0
    while round(sample_count * fps / p["sample_fps"]) < count:
        sample_count += 1
    last_model_sample_index = _last_model_sample_index(
        sample_count, p["frames"], p["stride_frames"]
    )
    if last_model_sample_index < 0:
        model_capture.release()
        if pose_capture is not model_capture:
            pose_capture.release()
        raise DetectionError("video_incompatible")
    streams = {}
    pose_samples = []
    previous_poses = []
    frame_index, next_sample = 0, 0
    # The upstream extractor removes slots 1, 14, and 15. Place the reviewed
    # 15-point model order into its surviving slots before calling it.
    kept = [i for i in range(18) if i not in (1, 14, 15)]
    try:
        with torch.inference_mode():
            while True:
                model_ok, model_frame = model_capture.read()
                if same_source:
                    pose_ok, pose_frame = model_ok, model_frame
                else:
                    pose_ok, pose_frame = pose_capture.read()
                if model_ok != pose_ok:
                    raise DetectionError("truncated_video")
                if not model_ok:
                    break
                index = frame_index
                frame_index += 1
                timestamp = model_capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                pose_timestamp = pose_capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if (
                    abs(timestamp - index / fps) > max(0.05, 1 / fps)
                    or abs(pose_timestamp - timestamp) > max(0.05, 1 / fps)
                    or model_frame.shape != pose_frame.shape
                ):
                    raise DetectionError("video_incompatible")
                if index < round(next_sample * fps / p["sample_fps"]):
                    continue
                next_sample += 1
                if next_sample - 1 > last_model_sample_index:
                    continue
                sample_index = next_sample - 1
                heatmaps, pafs, scale, pad = infer_fast(
                    pose, pose_frame, int(p["pose_height"]), 8, 4, True
                )
                by_type, total = [], 0
                for k in range(18):
                    total += extract_keypoints(heatmaps[:, :, k], by_type, total)
                entries, points = group_keypoints(by_type, pafs)
                current_poses = []
                keypoints_by_pose = {}
                for entry in entries:
                    keypoints = _sanitize_keypoints(
                        _keypoints_for_entry(entry, points, scale, pad),
                        pose_frame.shape[1],
                        pose_frame.shape[0],
                        p["min_keypoint_score"],
                    )
                    tracked_pose = Pose(
                        keypoints[:, :2].copy(), float(keypoints[:, 2].mean())
                    )
                    current_poses.append(tracked_pose)
                    keypoints_by_pose[id(tracked_pose)] = keypoints

                if current_poses:
                    track_poses(
                        previous_poses, current_poses, threshold=3, smooth=False
                    )
                else:
                    previous_poses = []

                frame_tracks = {}
                frame_rows = {}
                model_frame_for_patches = (
                    cv2.cvtColor(model_frame, cv2.COLOR_BGR2RGB)
                    if p["color_order"] == "RGB"
                    else model_frame
                )
                for tracked_pose in current_poses:
                    keypoints = keypoints_by_pose[id(tracked_pose)]
                    track_id = tracked_pose.id
                    if track_id not in streams:
                        streams[track_id] = {
                            "label": f"Track {len(streams) + 1}",
                            "buffer": [],
                            "buffer_start_index": sample_index,
                            "active": True,
                            "rows": [],
                            "unscored_windows": [],
                            "strongest_window": None,
                        }
                    stream = streams[track_id]
                    label = stream["label"]
                    frame_tracks[label] = keypoints.copy()
                    missing = _missing_required_keypoints(
                        keypoints,
                        required_keypoints,
                        pose_frame.shape[1],
                        pose_frame.shape[0],
                        p["min_keypoint_score"],
                    )
                    if missing:
                        frame_rows[track_id] = {
                            "reason": "incomplete_pose"
                        }
                        continue

                    reordered = keypoints.copy()
                    reordered[kept] = keypoints[p["patch_order"]]
                    patch = patches_module.extract_patches(
                        model_frame_for_patches,
                        reordered,
                        kernel_size=int(p["patch_kernel_size"]),
                        kernel_sigma=float(p["patch_sigma"]),
                        scale=float(p["patch_scale"]),
                    )
                    if patch.shape != (15, 32, 32, 3) or not np.isfinite(patch).all():
                        raise DetectionError("invalid_patch")
                    if blur_strength_percent:
                        patch = blur_rgb_patches(patch, blur_strength_percent, cv2)
                    kpts = keypoints[p["keypoint_order"]].copy()
                    kpts[:, :2] *= p["coordinate_scale"]
                    frame_rows[track_id] = {
                        "patches": patch.transpose(0, 3, 1, 2).astype(np.float32)
                        * p["pixel_scale"],
                        "coordinates": kpts,
                        "keypoints": keypoints.copy(),
                        "timestamp": index / fps,
                    }

                for track_id, stream in streams.items():
                    if not stream["active"]:
                        continue
                    sample = frame_rows.get(track_id, {"reason": "missing_pose"})
                    stream["buffer"].append(sample)
                    if len(stream["buffer"]) == p["frames"]:
                        window, reason = _complete_subject_window(stream["buffer"])
                        start_time = stream["buffer_start_index"] / p["sample_fps"]
                        end_time = min(
                            duration,
                            (stream["buffer_start_index"] + p["frames"])
                            / p["sample_fps"],
                        )
                        if reason:
                            stream["unscored_windows"].append(
                                {
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "reason": reason,
                                }
                            )
                        else:
                            patch_tensor = torch.from_numpy(
                                np.stack([row["patches"] for row in window])[None]
                            )
                            keypoint_tensor = torch.from_numpy(
                                np.stack([row["coordinates"] for row in window])[None]
                            )
                            prediction = model(patch_tensor, keypoint_tensor)
                            if prediction.numel() != 1:
                                raise DetectionError("invalid_model_output")
                            score = prediction.item()
                            stream["rows"].append(
                                {
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "raw_score": score,
                                }
                            )
                            if (
                                stream["strongest_window"] is None
                                or score > stream["strongest_window"][0]
                            ):
                                stream["strongest_window"] = (
                                    score,
                                    len(stream["rows"]) - 1,
                                    patch_tensor,
                                    keypoint_tensor,
                                    [row["timestamp"] for row in window],
                                )
                        stride = p["stride_frames"]
                        del stream["buffer"][:stride]
                        stream["buffer_start_index"] += stride
                    if sample.get("reason") == "missing_pose":
                        stream["active"] = False
                if current_poses:
                    previous_poses = current_poses
                pose_samples.append((index / fps, frame_tracks))
    finally:
        if pose_capture is not model_capture:
            pose_capture.release()
        model_capture.release()

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
        "privacy_input": "unblurred RGB patches and pose coordinates" if blur_strength_percent == 0 else "individually blurred RGB patches and pose coordinates",
        "blur_strength_percent": blur_strength_percent,
        "postprocessing": "per-window threshold; score is not calibrated",
    }
    subjects = []
    for stream in streams.values():
        rows = stream["rows"]
        unscored_windows = stream["unscored_windows"]
        strongest_window = stream["strongest_window"]
        if strongest_window is not None:
            score, row_index, patch_tensor, keypoint_tensor, evidence_times = strongest_window
            evidence = _vsvig_gradcam(
                model,
                patch_tensor,
                keypoint_tensor,
                evidence_times,
                contract["threshold"],
            )
            evidence["pose_samples"] = [
                {
                    "timestamp": round(timestamp, 4),
                    "points": [
                        {
                            "patch_index": patch_index,
                            "x": round(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        float(
                                            keypoint_tensor[
                                                0, frame_index, patch_index, 0
                                            ]
                                        )
                                        / p["width"],
                                    ),
                                ),
                                5,
                            ),
                            "y": round(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        float(
                                            keypoint_tensor[
                                                0, frame_index, patch_index, 1
                                            ]
                                        )
                                        / p["height"],
                                    ),
                                ),
                                5,
                            ),
                            "confidence": round(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        float(
                                            keypoint_tensor[
                                                0, frame_index, patch_index, 2
                                            ]
                                        ),
                                    ),
                                ),
                                4,
                            ),
                        }
                        for patch_index in range(15)
                    ],
                }
                for frame_index, timestamp in enumerate(evidence_times)
            ]
            rows[row_index]["model_evidence"] = evidence

        track_result = (
            validate_predictions(rows, duration, metadata)
            if rows
            else {
                "model": metadata,
                "predictions": [],
                "timeline": [],
                "intervals": [],
                "events": [],
                "recording_probability_available": False,
            }
        )
        reasons = {window["reason"] for window in unscored_windows}
        track_result.update(
            {
                "subject_id": stream["label"].lower().replace(" ", "-"),
                "label": stream["label"],
                "status": "scored" if rows else "unscored",
                "unavailable_reason": (
                    None
                    if rows
                    else "incomplete_pose"
                    if "incomplete_pose" in reasons
                    else "missing_pose"
                    if "missing_pose" in reasons
                    else "no_usable_windows"
                ),
                "unscored_windows": unscored_windows,
            }
        )
        subjects.append(track_result)

    if len(subjects) == 1 and subjects[0]["status"] == "scored":
        result = {
            field: subjects[0][field]
            for field in (
                "model",
                "predictions",
                "timeline",
                "intervals",
                "events",
                "summary",
                "recording_probability_available",
            )
        }
    else:
        result = {
            "model": metadata,
            "predictions": [],
            "timeline": [],
            "intervals": [],
            "events": [],
            "recording_probability_available": False,
        }
    result["subjects"] = subjects
    result["duration_seconds"] = frame_index / fps
    result["fps"] = fps
    result["frame_count"] = frame_index
    if visualization_output is not None:
        result["visualization"] = render_visualization(
            pose_source or model_source,
            visualization_output,
            pose_samples,
            unblurred=blur_strength_percent == 0,
        )
    else:
        result["visualization"] = {
            "available": False,
            "media_type": "video/mp4",
            "audio_included": False,
            "privacy_method": "tracked-face-blur-with-full-frame-fallback-and-skeleton-overlay",
            "overlay": {"skeleton": True, "model_score": False, "event_markers": False},
            "frontend_overlay": {"model_score": True, "event_markers": True},
        }
    return result


def inspect_pose_readiness(
    source_path: Path,
    *,
    allow_letterbox_adaptation: bool = False,
) -> dict:
    """Check the first VSViG window with the pinned pose model only."""

    root, contract = load_contract()
    import cv2
    import numpy as np
    import torch

    _configure_torch_backend(torch)
    torch.set_num_threads(2)
    sys.path.insert(0, str(root / "openpose"))
    from demo import infer_fast
    from models.with_mobilenet import PoseEstimationWithMobileNet
    from modules.keypoints import extract_keypoints, group_keypoints
    from modules.pose import Pose, track_poses

    pose = PoseEstimationWithMobileNet()
    checkpoint = torch.load(root / "pose.pth", map_location="cpu", weights_only=True)
    pose.load_state_dict(checkpoint.get("state_dict", checkpoint), strict=True)
    pose.eval()

    preprocessing = contract["preprocessing"]
    if source_path.is_symlink() or not source_path.is_file():
        raise DetectionError("video_incompatible")
    capture = cv2.VideoCapture(str(source_path))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    required_frames = int(preprocessing["frames"])
    sample_fps = float(preprocessing["sample_fps"])
    needs_adaptation = (width, height) != (
        preprocessing["width"],
        preprocessing["height"],
    )
    if (
        not capture.isOpened()
        or not math.isfinite(fps)
        or fps < sample_fps
        or fps > VIDEO_MAX_FPS
        or frame_count <= 0
        or frame_count > VIDEO_MAX_FRAMES
        or width <= 0
        or height <= 0
        or width > VIDEO_MAX_WIDTH
        or height > VIDEO_MAX_HEIGHT
        or width * height > VIDEO_MAX_WIDTH * VIDEO_MAX_HEIGHT
        or (needs_adaptation and not allow_letterbox_adaptation)
        or frame_count / fps < required_frames / sample_fps
        or frame_count / fps > VIDEO_MAX_DURATION_SECONDS
    ):
        capture.release()
        raise DetectionError("video_incompatible")

    required_keypoints = sorted(
        set(preprocessing["keypoint_order"]) | set(preprocessing["patch_order"])
    )
    label_by_index = dict(
        zip(preprocessing["keypoint_order"], preprocessing["patch_labels"])
    )
    missing_landmarks = {label: 0 for label in preprocessing["patch_labels"]}
    frames_without_person = 0
    frames_with_multiple_people = 0
    frames_with_tracking_break = 0
    frames_with_incomplete_pose = 0
    tracks = {}
    previous_poses = []
    frame_index = 0
    next_sample = 0
    checked_frames = 0
    timestamp_origin = None
    resized_width = resized_height = pad_x = pad_y = 0
    if needs_adaptation:
        from backend.app.video_privacy.processor import model_frame_layout

        resized_width, resized_height, pad_x, pad_y = model_frame_layout(width, height)

    try:
        with torch.inference_mode():
            while checked_frames < required_frames:
                ok, frame = capture.read()
                if not ok:
                    raise DetectionError("video_incompatible")
                index = frame_index
                frame_index += 1
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if timestamp_origin is None:
                    timestamp_origin = timestamp
                if (
                    not math.isfinite(timestamp)
                    or not math.isfinite(timestamp_origin)
                    or abs(timestamp - timestamp_origin - index / fps)
                    > max(0.05, 1 / fps)
                ):
                    raise DetectionError("video_incompatible")
                if index < round(next_sample * fps / sample_fps):
                    continue
                next_sample += 1
                checked_frames += 1
                if needs_adaptation:
                    frame = cv2.resize(
                        frame,
                        (resized_width, resized_height),
                        interpolation=(
                            cv2.INTER_LINEAR
                            if resized_width >= width and resized_height >= height
                            else cv2.INTER_AREA
                        ),
                    )
                    model_frame = np.zeros(
                        (
                            preprocessing["height"],
                            preprocessing["width"],
                            3,
                        ),
                        dtype=np.uint8,
                    )
                    model_frame[
                        pad_y : pad_y + resized_height,
                        pad_x : pad_x + resized_width,
                    ] = frame
                    frame = model_frame

                heatmaps, pafs, scale, pad = infer_fast(
                    pose, frame, int(preprocessing["pose_height"]), 8, 4, True
                )
                by_type, total = [], 0
                for joint_index in range(18):
                    total += extract_keypoints(
                        heatmaps[:, :, joint_index], by_type, total
                    )
                entries, points = group_keypoints(by_type, pafs)
                if len(entries) == 0:
                    frames_without_person += 1
                    previous_poses = []
                    continue
                if len(entries) > 1:
                    frames_with_multiple_people += 1

                current_poses = []
                keypoints_by_pose = {}
                for entry in entries:
                    keypoints = _sanitize_keypoints(
                        _keypoints_for_entry(entry, points, scale, pad),
                        frame.shape[1],
                        frame.shape[0],
                        preprocessing["min_keypoint_score"],
                    )
                    tracked_pose = Pose(
                        keypoints[:, :2].copy(), float(keypoints[:, 2].mean())
                    )
                    current_poses.append(tracked_pose)
                    keypoints_by_pose[id(tracked_pose)] = keypoints
                previous_ids = {tracked_pose.id for tracked_pose in previous_poses}
                track_poses(
                    previous_poses, current_poses, threshold=3, smooth=False
                )
                if previous_ids and any(
                    tracked_pose.id not in previous_ids
                    for tracked_pose in current_poses
                ):
                    frames_with_tracking_break += 1

                missing_this_frame = set()
                for tracked_pose in current_poses:
                    track_id = tracked_pose.id
                    keypoints = keypoints_by_pose[id(tracked_pose)]
                    track = tracks.setdefault(
                        track_id,
                        {
                            "first_frame": checked_frames - 1,
                            "last_frame": checked_frames - 1,
                            "frames": 0,
                            "complete_frames": 0,
                        },
                    )
                    track["last_frame"] = checked_frames - 1
                    track["frames"] += 1
                    missing = _missing_required_keypoints(
                        keypoints,
                        required_keypoints,
                        frame.shape[1],
                        frame.shape[0],
                        preprocessing["min_keypoint_score"],
                    )
                    if missing:
                        missing_this_frame.update(missing)
                    else:
                        track["complete_frames"] += 1
                if missing_this_frame:
                    frames_with_incomplete_pose += 1
                    for landmark_index in missing_this_frame:
                        missing_landmarks[label_by_index[landmark_index]] += 1
                previous_poses = current_poses
    finally:
        capture.release()

    missing_landmarks = {
        label: count for label, count in missing_landmarks.items() if count
    }
    usable_tracks = sum(
        track["first_frame"] == 0
        and track["last_frame"] == required_frames - 1
        and track["frames"] == required_frames
        and track["complete_frames"] == required_frames
        for track in tracks.values()
    )
    ready = checked_frames == required_frames and usable_tracks > 0
    return {
        "ready": ready,
        "checked_frames": checked_frames,
        "required_frames": required_frames,
        "tracks_seen": len(tracks),
        "usable_tracks": usable_tracks,
        "window_seconds": required_frames / sample_fps,
        "frames_without_person": frames_without_person,
        "frames_with_multiple_people": frames_with_multiple_people,
        "frames_with_tracking_break": frames_with_tracking_break,
        "frames_with_incomplete_pose": frames_with_incomplete_pose,
        "missing_landmarks": missing_landmarks,
    }


def run_pose_preview(
    blurred_source: Path,
    visualization_output: Path,
    preview_output: Path,
) -> dict:
    """Overlay single-person OpenPose evidence on an already-blurred video.

    This preview-only path deliberately does not load VSViG or produce a
    prediction. It accepts the video-privacy bounds, not the stricter VSViG
    1920×1080 admission contract.
    """

    root, contract = load_contract()
    import cv2
    import numpy as np
    import torch

    _configure_torch_backend(torch)
    torch.set_num_threads(2)
    sys.path.insert(0, str(root / "openpose"))
    from demo import infer_fast
    from models.with_mobilenet import PoseEstimationWithMobileNet
    from modules.keypoints import extract_keypoints, group_keypoints
    from modules.pose import Pose, track_poses

    pose = PoseEstimationWithMobileNet()
    checkpoint = torch.load(root / "pose.pth", map_location="cpu", weights_only=True)
    pose.load_state_dict(checkpoint.get("state_dict", checkpoint), strict=True)
    pose.eval()

    capture = cv2.VideoCapture(str(blurred_source))
    if not capture.isOpened() or visualization_output.is_symlink() or preview_output.is_symlink():
        capture.release()
        raise DetectionError("video_incompatible")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps > 0 else math.inf
    if (
        not math.isfinite(fps)
        or fps < VIDEO_MIN_FPS
        or fps > VIDEO_MAX_FPS
        or frame_count <= 0
        or frame_count > VIDEO_MAX_FRAMES
        or not math.isfinite(duration)
        or duration <= 0
        or duration > VIDEO_MAX_DURATION_SECONDS
        or width <= 0
        or height <= 0
        or width > VIDEO_MAX_WIDTH
        or height > VIDEO_MAX_HEIGHT
    ):
        capture.release()
        raise DetectionError("video_incompatible")

    sample_fps = float(contract["preprocessing"]["sample_fps"])
    pose_height = int(contract["preprocessing"]["pose_height"])
    min_keypoint_score = float(contract["preprocessing"]["min_keypoint_score"])
    pose_samples: list[tuple[float, np.ndarray]] = []
    previous_poses = []
    tracking_stopped = False
    sampled_frames = 0
    frame_index = 0
    next_sample = 0
    try:
        with torch.inference_mode():
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                index = frame_index
                frame_index += 1
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if not math.isfinite(timestamp) or abs(timestamp - index / fps) > max(0.05, 1 / fps):
                    raise DetectionError("video_incompatible")
                if index < round(next_sample * fps / sample_fps):
                    continue
                next_sample += 1
                sampled_frames += 1
                if tracking_stopped:
                    continue

                heatmaps, pafs, scale, pad = infer_fast(
                    pose, frame, pose_height, 8, 4, True
                )
                by_type, total = [], 0
                for joint_index in range(18):
                    total += extract_keypoints(
                        heatmaps[:, :, joint_index], by_type, total
                    )
                entries, points = group_keypoints(by_type, pafs)
                if len(entries) != 1:
                    if len(entries) > 1 or previous_poses:
                        tracking_stopped = True
                    continue

                keypoints = np.zeros((18, 3), dtype=np.float32)
                incomplete = False
                for joint_index, point_id in enumerate(entries[0][:18]):
                    if point_id < 0:
                        incomplete = True
                        break
                    point = points[int(point_id)]
                    keypoints[joint_index] = (
                        (point[0] * 2 - pad[1]) / scale,
                        (point[1] * 2 - pad[0]) / scale,
                        point[2],
                    )
                if (
                    incomplete
                    or (keypoints[:, 2] < min_keypoint_score).any()
                    or (keypoints[:, :2] < 0).any()
                    or (keypoints[:, 0] >= width).any()
                    or (keypoints[:, 1] >= height).any()
                ):
                    if previous_poses:
                        tracking_stopped = True
                    continue
                try:
                    previous_poses = _track_single_pose(
                        previous_poses, keypoints, Pose, track_poses
                    )
                except DetectionError:
                    tracking_stopped = True
                    continue
                pose_samples.append((index / fps, keypoints.copy()))
    finally:
        capture.release()

    if frame_index != frame_count:
        raise DetectionError("truncated_video")
    visualization = render_visualization(
        blurred_source,
        visualization_output,
        pose_samples,
        preview_path=preview_output,
    )
    return {
        "sampled_frames": sampled_frames,
        "detected_frames": len(pose_samples),
        "tracking_stopped": tracking_stopped,
        "visualization": visualization,
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) == 5 and sys.argv[1] == "--pose-readiness":
            result_path = Path(sys.argv[3])
            if sys.argv[4] not in {"0", "1"} or result_path.exists() or result_path.is_symlink():
                raise DetectionError("runtime_incompatible")
            result = inspect_pose_readiness(
                Path(sys.argv[2]), allow_letterbox_adaptation=sys.argv[4] == "1"
            )
            descriptor = os.open(
                result_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(result, output, allow_nan=False)
        elif len(sys.argv) == 6 and sys.argv[1] == "--pose-preview":
            preview = run_pose_preview(
                Path(sys.argv[2]), Path(sys.argv[4]), Path(sys.argv[5])
            )
            Path(sys.argv[3]).write_text(
                json.dumps(preview, allow_nan=False), encoding="utf-8"
            )
        elif len(sys.argv) in {5, 6}:
            result = run(
                Path(sys.argv[1]),
                Path(sys.argv[3]),
                pose_source=Path(sys.argv[4]),
                blur_strength_percent=int(sys.argv[5]) if len(sys.argv) == 6 else 100,
            )
            Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))
        elif len(sys.argv) == 4:
            visualization_output = Path(sys.argv[3])
            result = run(Path(sys.argv[1]), visualization_output)
            Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))
        elif len(sys.argv) == 3:
            result = run(Path(sys.argv[1]))
            Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))
        else:
            raise DetectionError("runtime_incompatible")
    except DetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except Exception:
        # Upstream exceptions can include private paths; never forward them.
        print("runtime_incompatible", file=sys.stderr)
        sys.exit(2)
