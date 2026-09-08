"""Verify a Keras H5 artifact before creating a reviewed model contract.

This research-only command never guesses training preprocessing or score
semantics. Those values must be supplied explicitly by the researcher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from backend.app.eeg.model_input import (
    MODEL_CHANNELS,
    MODEL_SAMPLING_RATE,
    WINDOW_SECONDS,
    WINDOW_STEP_SECONDS,
)
from backend.app.ml.h5_compat import h5_custom_objects


def _shape(value: object) -> list[int | None]:
    """Convert a Keras shape object into JSON-compatible dimensions."""

    return [None if item is None else int(item) for item in tuple(value)]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest used to identify the reviewed artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_model(model_path: Path) -> dict[str, object]:
    """Load an H5 model and return only facts inspectable from the artifact.

    Raises
    ------
    RuntimeError
        Raised when TensorFlow is unavailable or the artifact shape is
        incompatible with the fixed MDS01 model contract.
    """

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError("Install backend/requirements-research.txt first.") from exc

    try:
        model = tf.keras.models.load_model(
            model_path,
            compile=False,
            custom_objects=h5_custom_objects(tf),
        )
    except Exception as exc:
        raise RuntimeError("The H5 artifact could not be loaded.") from exc

    input_shape = _shape(model.input_shape)
    output_shape = _shape(model.output_shape)
    if input_shape != [None, 1024, 18] or output_shape != [None, 1]:
        raise RuntimeError(
            f"Expected input [None, 1024, 18] and output [None, 1]; got {input_shape} and {output_shape}."
        )

    input_dtype = str(getattr(model.inputs[0], "dtype", "unknown"))
    output_dtype = str(getattr(model.outputs[0], "dtype", "unknown"))
    if input_dtype != "float32":
        raise RuntimeError(f"Expected float32 model input; got {input_dtype}.")

    smoke_input = np.zeros((2, 1024, 18), dtype=np.float32)
    smoke_output = np.asarray(model.predict(smoke_input, verbose=0))
    if smoke_output.shape != (2, 1):
        raise RuntimeError(f"Expected smoke-test output shape (2, 1); got {smoke_output.shape}.")
    if not np.isfinite(smoke_output).all() or np.any((smoke_output < 0) | (smoke_output > 1)):
        raise RuntimeError("The H5 model returned non-finite or out-of-range smoke-test scores.")

    activation = getattr(getattr(model.layers[-1], "activation", None), "__name__", "unknown")
    return {
        "model_path": str(model_path),
        "artifact_sha256": _sha256(model_path),
        "input_shape": input_shape[1:],
        "output_shape": output_shape[1:],
        "input_dtype": input_dtype,
        "output_dtype": output_dtype,
        "last_layer_activation": activation,
        "output_semantics_candidate": "seizure-probability" if activation == "sigmoid" else "unknown",
        "smoke_test_score_range": [float(smoke_output.min()), float(smoke_output.max())],
    }


def main() -> int:
    """Inspect an H5 file and optionally write an explicitly reviewed contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--training-preprocessing")
    parser.add_argument("--model-name")
    parser.add_argument("--model-version")
    parser.add_argument("--window-stride-seconds", type=float, default=WINDOW_STEP_SECONDS)
    parser.add_argument("--write-contract", type=Path)
    args = parser.parse_args()

    report = inspect_model(args.model)
    print(json.dumps(report, indent=2))
    if args.write_contract is None:
        print("No contract written: score semantics, threshold, and preprocessing still require review.")
        return 0
    if report["output_semantics_candidate"] != "seizure-probability":
        raise SystemExit("Refusing to write a contract for an output without sigmoid probability semantics.")
    if args.threshold is None or not 0 <= args.threshold <= 1:
        raise SystemExit("--threshold in [0, 1] is required to write a reviewed contract.")
    if not args.training_preprocessing:
        raise SystemExit("--training-preprocessing is required to write a reviewed contract.")
    contract = {
        **report,
        "model_name": args.model_name or args.model.stem,
        "model_version": args.model_version or "review-required",
        "artifact_sha256": report["artifact_sha256"],
        "output_semantics": "seizure-probability",
        "threshold": args.threshold,
        "score_type": "uncalibrated_probability",
        "calibration_method": None,
        "calibration_status": "not_available",
        "calibration_profiles": {},
        "training_preprocessing": args.training_preprocessing,
        "channel_order": list(MODEL_CHANNELS),
        "sampling_rate": MODEL_SAMPLING_RATE,
        "window_seconds": WINDOW_SECONDS,
        "window_stride_seconds": args.window_stride_seconds,
        "input_dtype": "float32",
        "reviewed": False,
    }
    args.write_contract.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote an unreviewed contract draft to {args.write_contract}; set reviewed=true only after human review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
