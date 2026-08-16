"""Model runtime selection.

The real model adapter is intentionally not invented until its artifact and
training-time preprocessing are supplied.
"""

from __future__ import annotations

from backend.app.core.config import MODEL_RUNTIME
from backend.app.ml.interface import InferenceService
from backend.app.ml.stub_inference import StubInferenceService


def get_inference_service() -> InferenceService:
    if MODEL_RUNTIME == "stub":
        return StubInferenceService()
    raise RuntimeError(
        "MODEL_RUNTIME is not 'stub', but no real model adapter has been supplied."
    )

