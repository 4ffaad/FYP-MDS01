"""CHB-MIT discovery, seizure labels, and leakage-evaluation helpers."""

from __future__ import annotations

from pathlib import Path
import re


SUBJECTS = tuple(f"chb{index:02d}" for index in range(1, 11))
WINDOW_SECONDS = 4.0


def summary_annotations(text: str) -> dict[str, list[tuple[float, float]]]:
    """Parse safe per-recording seizure intervals from a CHB-MIT summary."""

    annotations: dict[str, list[tuple[float, float]]] = {}
    filename: str | None = None
    expected_count: int | None = None
    starts: list[float] = []
    ends: list[float] = []

    def store_current() -> None:
        if filename is None:
            return
        if len(starts) != len(ends) or (expected_count is not None and expected_count != len(starts)):
            raise ValueError("CHB-MIT summary contains mismatched seizure intervals.")
        intervals = [(start, end) for start, end in zip(starts, ends) if end > start]
        if len(intervals) != len(starts):
            raise ValueError("CHB-MIT summary contains an invalid seizure interval.")
        annotations[Path(filename).name.lower()] = intervals

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("File Name:"):
            store_current()
            filename = line.partition(":")[2].strip()
            expected_count = None
            starts = []
            ends = []
        elif filename is not None and line.startswith("Number of Seizures in File:"):
            expected_count = int(line.rsplit(":", 1)[1].strip())
        elif filename is not None and (match := re.fullmatch(r"Seizure(?: \d+)? Start Time: (\d+(?:\.\d+)?) seconds", line)):
            starts.append(float(match.group(1)))
        elif filename is not None and (match := re.fullmatch(r"Seizure(?: \d+)? End Time: (\d+(?:\.\d+)?) seconds", line)):
            ends.append(float(match.group(1)))
    store_current()
    return annotations


def sidecar_annotations(data: bytes) -> list[tuple[float, float]]:
    """Parse CHB-MIT bracket intervals from a compact WFDB annotation file."""

    index = 0
    sample = 0
    resolution = 250.0
    starts: list[float] = []
    intervals: list[tuple[float, float]] = []
    while index + 2 <= len(data):
        word = int.from_bytes(data[index:index + 2], "little")
        index += 2
        annotation_type = word >> 10
        interval = word & 0x03FF
        if word == 0:
            break
        if annotation_type == 59:  # WFDB SKIP stores a word-swapped signed 32-bit interval.
            if index + 4 > len(data):
                raise ValueError("CHB-MIT sidecar is truncated.")
            high = int.from_bytes(data[index:index + 2], "little")
            low = int.from_bytes(data[index + 2:index + 4], "little")
            index += 4
            skipped = (high << 16) | low
            if skipped & 0x80000000:
                skipped -= 0x100000000
            sample += skipped
            continue
        if annotation_type == 63:  # WFDB AUX text, including the sampling resolution header.
            end = index + interval
            if end > len(data):
                raise ValueError("CHB-MIT sidecar auxiliary data is truncated.")
            text = data[index:end].decode("ascii", errors="ignore")
            index = end + (interval % 2)
            if match := re.search(r"time resolution:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE):
                resolution = float(match.group(1))
            continue

        sample += interval
        if annotation_type == 32:
            starts.append(sample / resolution)
        elif annotation_type == 33 and starts:
            start = starts.pop()
            end = sample / resolution
            if end > start:
                intervals.append((start, end))
    if starts:
        raise ValueError("CHB-MIT sidecar contains an unclosed seizure interval.")
    return intervals


def sidecar_path(edf_path: Path) -> Path:
    """Return the PhysioNet CHB-MIT annotation sidecar for one EDF file."""

    return Path(f"{edf_path}.seizures")


def seizure_intervals(path: Path) -> list[tuple[float, float]]:
    """Read bracket-paired seizure intervals; a missing sidecar means no seizure."""

    if not path.exists():
        return []
    return sidecar_annotations(path.read_bytes())


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
