"""CHB-MIT discovery, seizure labels, and leakage-evaluation helpers."""

from __future__ import annotations

from pathlib import Path

import pyedflib


SUBJECTS = tuple(f"chb{index:02d}" for index in range(1, 11))
WINDOW_SECONDS = 4.0


def sidecar_path(edf_path: Path) -> Path:
    """Return the PhysioNet CHB-MIT annotation sidecar for one EDF file."""

    return Path(f"{edf_path}.seizures")


def seizure_intervals(path: Path) -> list[tuple[float, float]]:
    """Read bracket-paired seizure intervals; a missing sidecar means no seizure."""

    if not path.exists():
        return []
    reader = pyedflib.EdfReader(str(path))
    try:
        onsets, _durations, descriptions = reader.readAnnotations()
    finally:
        reader.close()
    starts: list[float] = []
    intervals: list[tuple[float, float]] = []
    for onset, description in zip(onsets, descriptions):
        marker = str(description).strip()
        if marker == "[":
            starts.append(float(onset))
        elif marker == "]" and starts:
            start = starts.pop()
            if float(onset) > start:
                intervals.append((start, float(onset)))
    if starts:
        raise ValueError(f"Unclosed seizure annotation in {path.name}.")
    return intervals


def seizure_window_labels(starts: list[float], intervals: list[tuple[float, float]]) -> list[int]:
    """Label windows positive when at least half their four seconds overlap a seizure."""

    labels: list[int] = []
    for start in starts:
        end = start + WINDOW_SECONDS
        labels.append(
            int(any(max(0.0, min(end, seizure_end) - max(start, seizure_start)) >= 2.0 for seizure_start, seizure_end in intervals))
        )
    return labels


def recording_test_names(recordings: list[Path]) -> set[str]:
    """Select a deterministic held-out recording per subject, never random windows."""

    ordered = sorted(recordings)
    if len(ordered) < 2:
        return set()
    return {path.name for path in ordered[::5] or ordered[-1:]}
