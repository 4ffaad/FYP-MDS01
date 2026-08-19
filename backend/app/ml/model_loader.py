"""Model runtime selection.

The real model adapter is intentionally not invented until its artifact and
training-time preprocessing are supplied.
"""

from __future__ import annotations

from backend.app.core.config import H5_CONTRACT_PATH, H5_MODEL_PATH, MODEL_RUNTIME
from backend.app.ml.h5_inference import H5InferenceService
from backend.app.ml.interface import InferenceService
from backend.app.ml.stub_inference import StubInferenceService


def get_inference_service() -> InferenceService:
    """Construct the configured inference adapter.

    Returns
    -------
    InferenceService
        Development stub when ``MODEL_RUNTIME=stub``.

    Raises
    ------
    RuntimeError
        Raised when a real runtime is requested before its model adapter has
        been implemented and supplied with an artifact.
    """

    if MODEL_RUNTIME == "stub":
        return StubInferenceService()
    if MODEL_RUNTIME == "h5":
        return H5InferenceService(H5_MODEL_PATH, H5_CONTRACT_PATH)
    raise RuntimeError(
        "MODEL_RUNTIME is not 'stub', but no real model adapter has been supplied."
    )
