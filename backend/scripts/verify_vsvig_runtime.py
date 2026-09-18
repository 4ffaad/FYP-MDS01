"""Fail-fast verification for the pinned VSViG bundle.

This check loads both published checkpoints and performs one tensor-only model
forward pass. It does not open video, access patient storage, or emit model
weights.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

# Support both ``python backend/scripts/...py`` and ``python -m ...``.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.video_detection.contract import DetectionError, load_contract
from backend.app.video_detection.runtime import module_from_file


def verify() -> dict:
    root, contract = load_contract()
    import cv2  # noqa: F401  # dependency check
    import numpy  # noqa: F401  # dependency check
    import torch

    torch.set_num_threads(2)
    openpose_root = root / "openpose"
    sys.path.insert(0, str(openpose_root))
    from demo import infer_fast  # noqa: F401  # import graph check
    from models.with_mobilenet import PoseEstimationWithMobileNet

    upstream = module_from_file("mds01_vsvig_verify", root / "vsvig/VSViG.py")
    partitions = torch.load(root / "dy_point_order.pt", map_location="cpu", weights_only=True)
    model = upstream.STViG(
        SimpleNamespace(
            dynamic=1,
            num_layer=[2, 2, 6, 2],
            output_channels=[24, 48, 96, 192],
            dynamic_point_order=partitions,
            expansion=2,
            pos_emb="stem",
        )
    )
    model.load_state_dict(
        torch.load(root / "VSViG-base.pth", map_location="cpu", weights_only=True),
        strict=True,
    )
    model.eval()

    pose = PoseEstimationWithMobileNet()
    pose_checkpoint = torch.load(root / "pose.pth", map_location="cpu", weights_only=True)
    pose.load_state_dict(pose_checkpoint.get("state_dict", pose_checkpoint), strict=True)
    pose.eval()

    frames = contract["preprocessing"]["frames"]
    with torch.inference_mode():
        output = model(
            torch.zeros((1, frames, 15, 3, 32, 32), dtype=torch.float32),
            torch.zeros((1, frames, 15, 3), dtype=torch.float32),
        )
    if output.numel() != 1:
        raise DetectionError("invalid_model_output")
    return {
        "model_name": "VSViG-base",
        "model_commit": contract["upstream_commit"],
        "pose_model": "Lightweight OpenPose",
        "pose_commit": contract["pose_commit"],
        "input_shape": [1, frames, 15, 3, 32, 32],
        "output_shape": list(output.shape),
    }


def main() -> int:
    try:
        print(json.dumps(verify(), sort_keys=True))
    except DetectionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        print("runtime_incompatible", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
