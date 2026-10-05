"""Format-dispatching EEG readers for EDF and Nicolet recordings."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

import numpy as np

from backend.app.eeg.edf_io import read_uniform_edf
from backend.app.eeg.contracts import (
    EEGInputContractError,
    MODEL_CHANNELS,
    MODEL_SAMPLING_RATE,
    require_model_sampling_rate,
)
from backend.app.eeg.legacy_nicolet import (
    NicoletEvent,
    NicoletVideoSyncSample,
    LEGACY_SOURCE_SAMPLING_RATE,
    coalesce_contiguous_segments,
    read_legacy_nicolet_events,
    read_legacy_nicolet_video_sync,
    read_uniform_legacy_nicolet,
    read_uniform_legacy_nicolet_segments,
    select_legacy_montage_channels,
    select_model_channels,
    _validate_segment_order,
    validate_legacy_nicolet,
)

_MAX_NICOLET_SIGNAL_VALUES = int(
    os.getenv("MDS01_MAX_NICOLET_SIGNAL_VALUES", "20000000")
)
_SAFE_DIAGNOSTIC_EXTENSIONS = frozenset(
    {".bdf", ".cnt", ".edf+", ".eeg", ".fif", ".set", ".vhdr", ".vmrk"}
)
if _MAX_NICOLET_SIGNAL_VALUES <= 0:
    raise RuntimeError("MDS01_MAX_NICOLET_SIGNAL_VALUES must be positive.")


@dataclass(frozen=True)
class EEGTechnicalMetadata:
    """Safe technical metadata shared by supported EEG formats."""

    format: str
    duration_seconds: float
    sampling_rate: int
    channel_count: int
    channel_labels: list[str]
    conversion_details: dict[str, object] | None = None


def _require_nicolet_file_without_symlinks(path: Path, *, label: str) -> Path:
    """Reject a Nicolet sidecar or data file that is itself a symlink."""

    candidate = path.absolute()
    try:
        mode = candidate.lstat().st_mode
    except FileNotFoundError as exc:
        raise ValueError(f"Nicolet {label} file is missing.") from exc
    if stat.S_ISLNK(mode):
        raise ValueError(f"Nicolet {label} files must not use symlinks.")
    if not stat.S_ISREG(mode):
        raise ValueError(f"Nicolet {label} file is not a regular file.")
    return candidate


def unsupported_eeg_format_message(path: str | Path) -> str:
    """Describe an unsupported extension without exposing the source path."""

    suffix = Path(path).suffix.lower()
    valid_suffix = suffix if suffix in _SAFE_DIAGNOSTIC_EXTENSIONS else "(unknown)"
    return (
        f"Unsupported EEG format (extension '{valid_suffix}'). Use EDF/EDF+, "
        "Nicolet .data with .head, or legacy Nicolet .e."
    )


def detect_eeg_format(path: str | Path) -> str:
    """Return the supported format for one private EEG primary file.

    Nicolet recordings are represented by a ``.data`` binary file and a
    same-stem ``.head`` sidecar. The sidecar is required before the reader is
    invoked so incomplete uploads fail closed.
    """

    candidate = Path(path)
    suffix = candidate.suffix.lower()
    if suffix == ".edf":
        return "edf"
    if suffix == ".data":
        header = candidate.with_suffix(".head")
        _require_nicolet_file_without_symlinks(candidate, label=".data")
        if not header.exists():
            raise ValueError("Nicolet .data input requires a matching .head file.")
        _require_nicolet_file_without_symlinks(header, label=".head")
        return "nicolet"
    if suffix == ".e":
        return "nicolet-e"
    raise ValueError(unsupported_eeg_format_message(candidate))


def _read_nicolet(path: Path, *, preload: bool):
    """Open one Nicolet recording through MNE's pinned reader."""

    try:
        import mne
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise RuntimeError("MNE is required for Nicolet EEG input.") from exc

    return mne.io.read_raw_nicolet(
        str(path),
        ch_type="eeg",
        preload=preload,
        verbose="ERROR",
    )


def _nicolet_technical_metadata(raw) -> tuple[int, list[str], float]:
    """Validate header fields and bound the signal array before loading it."""

    sampling_rate = require_model_sampling_rate(raw.info["sfreq"], "Nicolet .data input")
    labels = [str(label).strip() for label in raw.ch_names]
    if not labels or len(labels) != len(set(labels)) or any(not label for label in labels):
        raise ValueError("Nicolet channel labels are missing or ambiguous.")
    sample_count = int(raw.n_times)
    if sample_count <= 0:
        raise ValueError("Nicolet recording has no signal samples.")
    if sample_count * len(labels) > _MAX_NICOLET_SIGNAL_VALUES:
        raise ValueError("Nicolet recording exceeds the safe signal-size limit.")
    duration = float(sample_count / sampling_rate)
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError("Nicolet recording duration is invalid.")
    return int(round(sampling_rate)), labels, duration


def read_nicolet_bounded(path: str | Path):
    """Open and preload Nicolet data only after checking its aggregate size."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet":
        raise ValueError("Input is not a Nicolet .data recording.")
    raw = None
    try:
        raw = _read_nicolet(candidate, preload=False)
        _nicolet_technical_metadata(raw)
        raw.load_data()
        return raw
    except Exception:
        if raw is not None:
            raw.close()
        raise


def validate_nicolet(path: str | Path) -> EEGTechnicalMetadata:
    """Read only Nicolet technical metadata without loading all samples."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet":
        raise ValueError("Input is not a Nicolet .data recording.")
    raw = None
    try:
        raw = _read_nicolet(candidate, preload=False)
        sampling_rate, labels, duration = _nicolet_technical_metadata(raw)
        return EEGTechnicalMetadata(
            format="nicolet",
            duration_seconds=duration,
            sampling_rate=sampling_rate,
            channel_count=len(labels),
            channel_labels=labels,
        )
    except EEGInputContractError as exc:
        raise ValueError(str(exc)) from exc
    except Exception as exc:
        raise ValueError("Nicolet EEG files are unreadable or malformed.") from exc
    finally:
        if raw is not None:
            raw.close()


def validate_legacy_nicolet_e(path: str | Path) -> EEGTechnicalMetadata:
    """Read safe metadata from a legacy single-file Nicolet recording."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet-e":
        raise ValueError("Input is not a legacy Nicolet .e recording.")
    try:
        header = validate_legacy_nicolet(candidate)
        _validate_segment_order(
            header.segments,
            header.sampling_rate,
            header.total_samples,
        )
        if header.sampling_rate == MODEL_SAMPLING_RATE:
            select_model_channels(header)
        elif header.sampling_rate == LEGACY_SOURCE_SAMPLING_RATE:
            select_legacy_montage_channels(header)
        else:
            raise ValueError("Legacy Nicolet source sampling rate is unsupported.")
        duration = max(
            segment.start_seconds + segment.duration_seconds
            for segment in header.segments
        )
        analysis_segments = coalesce_contiguous_segments(
            header.segments, header.sampling_rate
        )
        has_time_gaps = len(analysis_segments) > 1
        model_segments: list[dict[str, int | float]] = []
        model_sample_start = 0
        for segment in analysis_segments:
            model_sample_count = (
                segment.sample_count * MODEL_SAMPLING_RATE
                + header.sampling_rate
                - 1
            ) // header.sampling_rate
            model_segments.append(
                {
                    "sample_start": model_sample_start,
                    "sample_count": model_sample_count,
                    "start_seconds": segment.start_seconds,
                    "duration_seconds": segment.duration_seconds,
                }
            )
            model_sample_start += model_sample_count
        return EEGTechnicalMetadata(
            format="nicolet-e",
            duration_seconds=duration,
            sampling_rate=MODEL_SAMPLING_RATE,
            channel_count=len(MODEL_CHANNELS),
            channel_labels=list(MODEL_CHANNELS),
            conversion_details={
                "source_sampling_rate_hz": header.sampling_rate,
                "source_channel_count": len(header.channels),
                "source_montage": (
                    "legacy_referential_10_20"
                    if header.sampling_rate == LEGACY_SOURCE_SAMPLING_RATE
                    else "reviewed_18_channel_contract"
                ),
                "electrode_aliases": "T3->T7,T4->T8,T5->P7,T6->P8",
                "bipolar_channels": "reviewed_18_channel_contract",
                "resampling": (
                    "polyphase_128_over_250_kaiser_beta_5"
                    if header.sampling_rate == LEGACY_SOURCE_SAMPLING_RATE
                    else "none"
                ),
                "signal_duration_seconds": sum(
                    segment.duration_seconds for segment in header.segments
                ),
                "timeline_duration_seconds": duration,
                "has_time_gaps": has_time_gaps,
                "model_segments": model_segments,
            },
        )
    except Exception as exc:
        raise ValueError("Legacy Nicolet EEG files are unreadable or malformed.") from exc


def read_uniform_nicolet(path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read Nicolet samples as ``(channels, samples)`` with safe metadata."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet":
        raise ValueError("Input is not a Nicolet .data recording.")
    raw = None
    try:
        raw = read_nicolet_bounded(candidate)
        sampling_rate, labels, _ = _nicolet_technical_metadata(raw)
        signals = np.asarray(raw.get_data(), dtype=np.float64)
        if signals.ndim != 2 or signals.shape[0] != len(labels) or not np.isfinite(signals).all():
            raise ValueError("Nicolet signal data is invalid.")
        return signals, sampling_rate, labels
    finally:
        if raw is not None:
            raw.close()


def read_uniform_legacy_eeg(path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read legacy Nicolet samples as ``(channels, samples)``."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet-e":
        raise ValueError("Input is not a legacy Nicolet .e recording.")
    try:
        signals, sampling_rate, labels = read_uniform_legacy_nicolet(candidate)
        if (
            signals.ndim != 2
            or signals.shape[0] != len(labels)
            or not labels
            or len(labels) != len(set(labels))
            or not np.isfinite(signals).all()
        ):
            raise ValueError("Legacy Nicolet signal data is invalid.")
        return signals, sampling_rate, labels
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Legacy Nicolet EEG files are unreadable or malformed.") from exc


def read_uniform_legacy_eeg_segments(
    path: str | Path,
) -> tuple[list[tuple[float, np.ndarray]], int, list[str]]:
    """Read validated Nicolet signal segments without joining acquisition gaps."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet-e":
        raise ValueError("Input is not a legacy Nicolet .e recording.")
    try:
        segments, sampling_rate, labels = read_uniform_legacy_nicolet_segments(candidate)
        if (
            not segments
            or not labels
            or len(labels) != len(set(labels))
            or any(
                signals.ndim != 2
                or signals.shape[0] != len(labels)
                or signals.shape[1] <= 0
                or not np.isfinite(signals).all()
                for _start_seconds, signals in segments
            )
        ):
            raise ValueError("Legacy Nicolet signal segments are invalid.")
        return segments, sampling_rate, labels
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Legacy Nicolet EEG files are unreadable or malformed.") from exc


def read_legacy_eeg_events(path: str | Path) -> tuple[NicoletEvent, ...]:
    """Read only sanitized legacy Nicolet event timing."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet-e":
        raise ValueError("Input is not a legacy Nicolet .e recording.")
    try:
        return read_legacy_nicolet_events(candidate)
    except Exception as exc:
        raise ValueError("Legacy Nicolet event data is unreadable or malformed.") from exc


def read_legacy_eeg_video_sync(
    path: str | Path, key: bytes, *, context: str = ""
) -> tuple[NicoletVideoSyncSample, ...]:
    """Read keyed video sync anchors only from a legacy Nicolet .e file."""

    candidate = Path(path)
    if detect_eeg_format(candidate) != "nicolet-e":
        raise ValueError("Input is not a legacy Nicolet .e recording.")
    try:
        return read_legacy_nicolet_video_sync(candidate, key, context=context)
    except Exception as exc:
        raise ValueError("Legacy Nicolet video sync data is unreadable or malformed.") from exc


def read_uniform_eeg(path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read either supported EEG format using one signal contract."""

    candidate = Path(path)
    eeg_format = detect_eeg_format(candidate)
    if eeg_format == "edf":
        return read_uniform_edf(candidate)
    if eeg_format == "nicolet-e":
        return read_uniform_legacy_eeg(candidate)
    return read_uniform_nicolet(candidate)
