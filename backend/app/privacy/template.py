"""PSD feature extraction for offline identity-attacker evaluation."""

from __future__ import annotations

import numpy as np
from scipy.signal import welch


PSD_BANDS = ((0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 45.0))


def psd_features(windows: np.ndarray, sampling_rate: int = 256) -> np.ndarray:
    """Return 90 log-bandpower features for ``(N, 1024, 18)`` EEG windows."""

    if windows.ndim != 3 or windows.shape[1:] != (1024, 18):
        raise ValueError("Template input must have shape (N, 1024, 18).")
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

