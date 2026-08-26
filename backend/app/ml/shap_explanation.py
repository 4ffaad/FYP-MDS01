"""Bounded SHAP explanations for the reviewed H5 EEG model.

SHAP is deliberately optional. A missing research dependency, background
tensor, or unsupported model operation disables attribution while leaving the
model score and alert timeline available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from backend.app.eeg.model_input import MODEL_CHANNELS, WINDOW_SECONDS, WINDOW_SAMPLES
from backend.app.ml.interface import WindowPrediction


class ShapExplanationError(RuntimeError):
    """Raised when a bounded SHAP explanation cannot be produced safely."""


def build_shap_explanations(
    *,
    model: Any,
    windows: np.ndarray,
    predictions: list[WindowPrediction],
    background_path: Path,
    threshold: float,
    max_windows: int = 3,
    time_bins: int = 32,
) -> dict[int, dict[str, Any]]:
    """Return research-only SHAP summaries for the highest flagged windows.

    Parameters
    ----------
    model : object
        TensorFlow/Keras model used for the final inference tensor.
    windows : numpy.ndarray
        Final model input after the selected privacy transformation, shaped
        ``(N, 1024, 18)``. Raw EDF samples are not accepted here.
    predictions : list[WindowPrediction]
        Persisted model-window outputs used to select flagged windows.
    background_path : pathlib.Path
        Reviewed ``.npy`` tensor used as the SHAP background dataset.
    threshold : float
        Persisted model alert threshold used for the explained window.
    max_windows : int
        Maximum number of high-scoring flagged windows to explain.
    time_bins : int
        Number of relative time bins in each attribution summary.

    Returns
    -------
    dict[int, dict[str, Any]]
        JSON-safe explanation payloads keyed by model window index. Empty when
        no model window is flagged.

    Raises
    ------
    ShapExplanationError
        Raised for missing dependencies, invalid background data, unsupported
        model output, or attribution shape mismatches. Callers may catch this
        error and retain score-only results.

    Privacy
    -------
    The output contains aggregate attributions only. It never contains EEG
    samples, paths, hashes, patient metadata, or the background tensor.
    """

    if windows.ndim != 3 or windows.shape[1:] != (WINDOW_SAMPLES, len(MODEL_CHANNELS)) or windows.dtype != np.float32:
        raise ShapExplanationError("SHAP requires the final float32 model tensor with shape (N, 1024, 18).")
    if max_windows < 1 or time_bins < 1 or time_bins > WINDOW_SAMPLES:
        raise ShapExplanationError("SHAP explanation limits are invalid.")

    flagged = sorted(
        (item for item in predictions if item.seizure_detected),
        key=lambda item: item.probability,
        reverse=True,
    )[:max_windows]
    if not flagged:
        return {}

    try:
        import shap
    except ImportError as exc:
        raise ShapExplanationError("The optional SHAP research dependency is unavailable.") from exc

    background = _load_background(background_path)
    try:
        explainer = shap.GradientExplainer(model, background)
        explained_windows = np.asarray(explainer.shap_values(
            windows[[item.window_index for item in flagged]],
        ))
    except Exception as exc:
        raise ShapExplanationError("SHAP could not explain this H5 model.") from exc

    attributions = _normalise_attributions(explained_windows, len(flagged))
    result: dict[int, dict[str, Any]] = {}
    for position, prediction in enumerate(flagged):
        result[prediction.window_index] = _summarise_attributions(
            prediction=prediction,
            attributions=attributions[position],
            threshold=threshold,
            time_bins=time_bins,
        )
    return result


def _load_background(path: Path) -> np.ndarray:
    """Load and validate a bounded reviewed SHAP background tensor."""

    try:
        background = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ShapExplanationError("A reviewed SHAP background tensor is required.") from exc
    if background.ndim != 3 or background.shape[1:] != (WINDOW_SAMPLES, len(MODEL_CHANNELS)):
        raise ShapExplanationError("The SHAP background tensor has an incompatible shape.")
    if background.dtype != np.float32 or not np.isfinite(background).all() or not len(background):
        raise ShapExplanationError("The SHAP background tensor must be finite float32 data.")
    if len(background) > 64:
        raise ShapExplanationError("The SHAP background tensor exceeds the 64-window limit.")
    return background


def _normalise_attributions(values: np.ndarray, count: int) -> np.ndarray:
    """Convert SHAP single-output variants to ``(N, 1024, 18)``."""

    # SHAP versions return either an array or a one-item list for one-output
    # models. The list is converted by the caller before this helper runs when
    # possible, but handling the extra output axis keeps the boundary strict.
    if values.ndim == 4 and values.shape[-1] == 1:
        values = values[..., 0]
    if values.ndim == 4 and values.shape[0] == 1:
        values = values[0]
    if values.shape != (count, WINDOW_SAMPLES, len(MODEL_CHANNELS)):
        raise ShapExplanationError("SHAP returned an incompatible attribution shape.")
    if not np.isfinite(values).all():
        raise ShapExplanationError("SHAP returned non-finite attributions.")
    return values.astype(np.float32, copy=False)


def _summarise_attributions(
    *,
    prediction: WindowPrediction,
    attributions: np.ndarray,
    threshold: float,
    time_bins: int,
) -> dict[str, Any]:
    """Reduce one attribution tensor into safe channel and time summaries."""

    absolute = np.abs(attributions)
    channel_scores = absolute.mean(axis=0)
    bin_edges = np.linspace(0, WINDOW_SAMPLES, time_bins + 1, dtype=np.int64)
    bins = []
    for index in range(time_bins):
        start_sample = int(bin_edges[index])
        end_sample = int(bin_edges[index + 1])
        values = absolute[start_sample:end_sample].mean(axis=0)
        bins.append({
            "start_seconds": float(index * WINDOW_SECONDS / time_bins),
            "end_seconds": float((index + 1) * WINDOW_SECONDS / time_bins),
            "channel_scores": [float(value) for value in values],
        })

    ranked = np.argsort(channel_scores)[::-1]
    return {
        "method": "shap-gradient",
        "is_clinical": False,
        "note": "Research attribution shows input sensitivity for this window; it is not a clinical explanation.",
        "window_index": prediction.window_index,
        "window_start_seconds": prediction.start_seconds,
        "window_end_seconds": prediction.end_seconds,
        "score": prediction.probability,
        "threshold": float(threshold),
        "channel_scores": [
            {"label": MODEL_CHANNELS[index], "mean_absolute_attribution": float(channel_scores[index])}
            for index in range(len(MODEL_CHANNELS))
        ],
        "top_channels": [MODEL_CHANNELS[index] for index in ranked[:5]],
        "time_bins": bins,
    }
