"""Experimental cancellable, lossy EEG transformations for research evaluation."""

from __future__ import annotations

import hashlib
import hmac

import numpy as np
from scipy.signal import welch


TRANSFORMATION_VERSION = "cancellable-signal-projection-v1"
MODEL_SHAPE = (1024, 18)
REMOVED_CHANNEL_DIMENSIONS = 3
QUANTIZATION_STEP = np.float32(1 / 16)
PSD_BANDS = ((0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 45.0))


def cancellable_signal_projection(windows: np.ndarray, key: bytes) -> np.ndarray:
    """Return a keyed, rank-reduced, quantized EEG tensor with model shape.

    The operation removes a secret three-dimensional channel subspace and
    quantizes the remaining values. It is deliberately lossy and has the same
    ``(N, 1024, 18)`` float32 contract as the seizure model so that both the
    detector and identity attacker can be evaluated on exactly this output.
    It is an experimental risk-reduction transform, not an anonymity proof.
    """

    if windows.ndim != 3 or windows.shape[1:] != MODEL_SHAPE:
        raise ValueError("Signal transformation input must have shape (N, 1024, 18).")
    if len(key) != 32:
        raise ValueError("Signal transformation requires a 32-byte key.")

    seed = int.from_bytes(
        hmac.new(key, TRANSFORMATION_VERSION.encode("utf-8"), hashlib.sha256).digest()[:8],
        "big",
    )
    removed_basis, _ = np.linalg.qr(
        np.random.default_rng(seed).normal(size=(MODEL_SHAPE[1], REMOVED_CHANNEL_DIMENSIONS))
    )
    projection = np.eye(MODEL_SHAPE[1], dtype=np.float32) - (removed_basis @ removed_basis.T).astype(np.float32)
    projected = np.einsum("ntc,cd->ntd", windows.astype(np.float32, copy=False), projection, optimize=True)
    return (
        np.rint(np.clip(projected, -5.0, 5.0) / QUANTIZATION_STEP) * QUANTIZATION_STEP
    ).astype(np.float32)


def psd_features(windows: np.ndarray, sampling_rate: int = 256) -> np.ndarray:
    """Return 90 log-bandpower features for offline identity evaluation."""

    if windows.ndim != 3 or windows.shape[1:] != MODEL_SHAPE:
        raise ValueError("PSD input must have shape (N, 1024, 18).")
    frequencies, power = welch(
        windows.transpose(0, 2, 1),
        fs=sampling_rate,
        nperseg=windows.shape[1],
        axis=-1,
    )
    features = [
        power[..., (frequencies >= low) & (frequencies < high)].mean(axis=-1)
        for low, high in PSD_BANDS
    ]
    return np.log10(np.maximum(np.stack(features, axis=-1), 1e-12)).reshape(len(windows), -1)
