"""Verify an H5 model before it may be enabled for private EEG inference."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def verify(model_path: Path, threshold: float, preprocessing: str) -> dict:
    """Load an H5 artifact and return observable facts for human contract review."""

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1].")
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError("Install backend/requirements-research.txt first.") from exc
    model = tf.keras.models.load_model(model_path, compile=False)
    if tuple(model.input_shape)[1:] != (1024, 18):
        raise RuntimeError(f"Expected H5 input (N, 1024, 18), got {model.input_shape}.")
    if tuple(model.output_shape)[1:] != (1,):
        raise RuntimeError(f"Expected one probability output, got {model.output_shape}.")
    output = np.asarray(model.predict(np.zeros((1, 1024, 18), dtype=np.float32), verbose=0)).reshape(-1)
    if len(output) != 1 or not 0 <= float(output[0]) <= 1:
        raise RuntimeError("H5 output is not a probability in [0, 1].")
    return {
        "reviewed": False,
        "model_name": model_path.stem,
        "model_version": "review-required",
        "input_shape": [1024, 18],
        "output_shape": [1],
        "output_semantics": "seizure-probability",
        "threshold": threshold,
        "training_preprocessing": preprocessing,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "review_note": "Set reviewed=true only after confirming training provenance and threshold.",
    }


def main() -> None:
    """Write an unreviewed contract record for a compatible H5 artifact."""

    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--preprocessing", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = verify(args.model, args.threshold, args.preprocessing)
    args.output.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
