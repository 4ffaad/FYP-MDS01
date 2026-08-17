"""Model runtime selection.

The real model adapter is intentionally not invented until its artifact and
training-time preprocessing are supplied.
"""

from __future__ import annotations

from backend.app.core.config import MODEL_RUNTIME
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
    raise RuntimeError(
        "MODEL_RUNTIME is not 'stub', but no real model adapter has been supplied."
    )
