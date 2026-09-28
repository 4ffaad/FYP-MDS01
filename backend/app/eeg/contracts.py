"""Reviewed EEG model-input contract constants and admission helpers."""

import math


class EEGInputContractError(ValueError):
    """Raised when an input cannot satisfy the reviewed model contract."""

MODEL_CHANNELS = (
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1", "FP1-F3", "F3-C3",
    "C3-P3", "P3-O1", "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
    "FP2-F8", "F8-T8", "T8-P8", "P8-O2", "FZ-CZ", "CZ-PZ",
)
MODEL_SAMPLING_RATE = 256


def require_model_sampling_rate(sampling_rate: int | float, source_name: str) -> int:
    """Require the reviewed rate when no approved resampling path exists."""

    try:
        rate = float(sampling_rate)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EEGInputContractError(
            f"{source_name} must use exactly {MODEL_SAMPLING_RATE} Hz; resampling is not configured."
        ) from exc
    if not math.isfinite(rate) or rate != MODEL_SAMPLING_RATE:
        raise EEGInputContractError(
            f"{source_name} must use exactly {MODEL_SAMPLING_RATE} Hz; resampling is not configured."
        )
    return MODEL_SAMPLING_RATE
