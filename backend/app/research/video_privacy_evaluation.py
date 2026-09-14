"""Aggregate utility comparison for raw and face-redacted VSViG inputs."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from backend.app.database.models.video import VideoPrivacyProfile
from backend.app.research.evaluation import build_metrics_report
from backend.app.video_privacy.processor import VideoPrivacyProcessor


def window_labels(predictions: list[dict[str, Any]], intervals: list[list[float]]) -> list[int]:
    """Label a model window positive when it overlaps a reviewed event interval."""

    return [
        int(any(float(item["start_time"]) < end and float(item["end_time"]) > start for start, end in intervals))
        for item in predictions
    ]


def load_manifest(path: Path, dataset_root: Path, split: str) -> list[dict[str, Any]]:
    """Load an approved manifest without returning patient paths or labels."""

    entries = json.loads(path.read_text())
    if not isinstance(entries, list):
        raise ValueError("Video evaluation manifest must be a JSON list.")
    selected: list[dict[str, Any]] = []
    owners: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict) or not all(key in item for key in ("video", "subject_id", "split", "seizure_intervals")):
            raise ValueError("Each video manifest entry needs video, subject_id, split, and seizure_intervals.")
        subject, entry_split = str(item["subject_id"]), str(item["split"])
        if subject in owners and owners[subject] != entry_split:
            raise ValueError("Video evaluation subjects must not span splits.")
        owners[subject] = entry_split
        candidate = (dataset_root / str(item["video"])).resolve()
        if not candidate.is_relative_to(dataset_root.resolve()) or not candidate.is_file():
            raise ValueError("A video manifest entry is outside or missing from the approved dataset root.")
        intervals = item["seizure_intervals"]
        if not isinstance(intervals, list) or any(
            not isinstance(interval, list) or len(interval) != 2 or float(interval[0]) < 0 or float(interval[0]) >= float(interval[1])
            for interval in intervals
        ):
            raise ValueError("Video seizure intervals must be [start_seconds, end_seconds] pairs.")
        if entry_split == split:
            selected.append({"path": candidate, "subject_id": subject, "intervals": intervals})
    if not selected:
        raise ValueError("No approved videos matched the requested evaluation split.")
    return selected


def evaluate_video_privacy(
    dataset_root: Path,
    manifest_path: Path,
    *,
    split: str = "test",
    seed: int = 0,
    runtime: Callable[[Path], dict[str, Any]] | None = None,
    processor: VideoPrivacyProcessor | None = None,
) -> dict[str, Any]:
    """Compare raw and face-redacted scores using only aggregate output."""

    records = load_manifest(manifest_path, dataset_root, split)
    if runtime is None:
        from backend.app.video_detection.runtime import run
        runtime = run
    processor = processor or VideoPrivacyProcessor()
    labels: list[int] = []
    raw_scores: list[float] = []
    protected_scores: list[float] = []
    subjects: list[str] = []
    duration_hours = 0.0
    threshold: float | None = None
    for record in records:
        raw = runtime(record["path"])
        with tempfile.TemporaryDirectory(prefix="mds01-video-eval-") as directory:
            protected_path = Path(directory) / "protected.mp4"
            preview_path = Path(directory) / "preview.jpg"
            transformed = processor.process(record["path"], protected_path, preview_path, VideoPrivacyProfile.FACE_REDACTED)
            if not transformed.usable:
                raise ValueError("Face redaction did not meet the evaluation privacy quality gate.")
            protected = runtime(protected_path)
        raw_windows, protected_windows = raw["predictions"], protected["predictions"]
        if len(raw_windows) != len(protected_windows) or any(
            raw_item["start_time"] != protected_item["start_time"] or raw_item["end_time"] != protected_item["end_time"]
            for raw_item, protected_item in zip(raw_windows, protected_windows)
        ):
            raise ValueError("Raw and protected video windows do not align.")
        item_labels = window_labels(raw_windows, record["intervals"])
        labels.extend(item_labels)
        raw_scores.extend(float(item["score"]) for item in raw_windows)
        protected_scores.extend(float(item["score"]) for item in protected_windows)
        subjects.extend([record["subject_id"]] * len(raw_windows))
        duration_hours += float(raw_windows[-1]["end_time"]) / 3600
        threshold = float(raw["model"]["threshold"])
    if threshold is None or not labels:
        raise ValueError("No usable labelled video windows were evaluated.")
    raw_metrics = build_metrics_report(labels=labels, scores=raw_scores, patient_ids=subjects, duration_hours=duration_hours, threshold=threshold, seed=seed)
    protected_metrics = build_metrics_report(labels=labels, scores=protected_scores, patient_ids=subjects, duration_hours=duration_hours, threshold=threshold, seed=seed)
    return {
        "dataset": "approved-video-manifest",
        "split": split,
        "subject_count": len(set(subjects)),
        "window_count": len(labels),
        "threshold": threshold,
        "privacy_method": "face-redaction",
        "raw_metrics": raw_metrics,
        "protected_metrics": protected_metrics,
        "mean_absolute_score_difference": sum(abs(left - right) for left, right in zip(raw_scores, protected_scores)) / len(labels),
        "threshold_agreement": sum((left >= threshold) == (right >= threshold) for left, right in zip(raw_scores, protected_scores)) / len(labels),
    }
