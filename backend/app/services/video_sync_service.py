"""Resolve owner-scoped video chunks against encrypted Nicolet sync anchors."""

from __future__ import annotations

import json
import math
import secrets
from statistics import median
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlmodel import Session, select

from backend.app.core.config import STORAGE_KEY_ENV
from backend.app.database.models.eeg import EEGRecording, EEGSession
from backend.app.database.models.video_detection import VideoDetectionJob
from backend.app.privacy.crypto import CryptoError, read_base64_key

_NONCE_BYTES = 12


class VideoSyncCryptoError(RuntimeError):
    """Raised when private VEEG synchronization data cannot be protected."""


def _sync_key() -> bytes:
    try:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"mds01-veeg-sync-v1",
            info=b"authenticated-sync-metadata/aes-gcm",
        ).derive(read_base64_key(STORAGE_KEY_ENV))
    except (CryptoError, ValueError) as exc:
        raise VideoSyncCryptoError("VEEG synchronization storage is unavailable.") from exc


def _aad(kind: str, owner_user_id: int, case_id: str, reference: str) -> bytes:
    return f"mds01-veeg-sync\0{kind}\0{owner_user_id}\0{case_id}\0{reference}".encode()


def _encrypt(
    kind: str,
    owner_user_id: int,
    case_id: str,
    reference: str,
    value: dict[str, Any],
) -> tuple[bytes, bytes]:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    plaintext = json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
    try:
        ciphertext = AESGCM(_sync_key()).encrypt(
            nonce, plaintext, _aad(kind, owner_user_id, case_id, reference)
        )
    except (TypeError, ValueError) as exc:
        raise VideoSyncCryptoError("VEEG synchronization metadata is invalid.") from exc
    return nonce, ciphertext


def decrypt_sync_payload(
    kind: str,
    owner_user_id: int,
    case_id: str,
    reference: str,
    nonce: bytes | None,
    ciphertext: bytes | None,
) -> dict[str, Any] | None:
    """Decrypt a validated sync object bound to its owner, case, and row."""

    if nonce is None or ciphertext is None or len(nonce) != _NONCE_BYTES:
        return None
    try:
        plaintext = AESGCM(_sync_key()).decrypt(
            nonce, ciphertext, _aad(kind, owner_user_id, case_id, reference)
        )
        value = json.loads(plaintext)
    except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, VideoSyncCryptoError):
        return None
    return value if isinstance(value, dict) else None


def encrypt_recording_manifest(
    recording: EEGRecording,
    *,
    owner_user_id: int,
    case_id: str,
    manifest: dict[str, Any],
) -> None:
    if recording.id is None:
        raise VideoSyncCryptoError("EEG recording must be saved before sync metadata.")
    recording.video_sync_nonce, recording.video_sync_ciphertext = _encrypt(
        "recording", owner_user_id, case_id, str(recording.id), manifest
    )
    recording.video_sync_status = "available"


def encrypt_job_mapping(
    job: VideoDetectionJob,
    *,
    owner_user_id: int,
    case_id: str,
    mapping: dict[str, Any],
) -> None:
    job.eeg_sync_nonce, job.eeg_sync_ciphertext = _encrypt(
        "video-job", owner_user_id, case_id, job.job_id, mapping
    )


def _valid_number(value: object, *, minimum: float | None = None) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and (minimum is None or value >= minimum)
    )


def match_sync_video_group(
    manifest: dict[str, Any],
    jobs: list[Any],
) -> dict[str, dict[str, Any]] | None:
    """Map every sync-referenced clip in one complete folder, failing closed."""

    markers = manifest.get("markers")
    segments = manifest.get("segments")
    if not isinstance(markers, list) or not markers or not isinstance(segments, list):
        return None

    samples_by_token: dict[str, list[dict[str, float]]] = {}
    for marker in markers:
        if not isinstance(marker, dict):
            return None
        token = marker.get("source_name_token")
        frame = marker.get("frame_index")
        clock_time = marker.get("eeg_clock_seconds")
        if (
            not isinstance(token, str)
            or len(token) != 64
            or any(character not in "0123456789abcdef" for character in token)
            or type(frame) is not int
            or frame < 0
            or not _valid_number(clock_time, minimum=-1)
        ):
            return None
        samples_by_token.setdefault(token, []).append(
            {"frame_index": float(frame), "eeg_clock_seconds": float(clock_time)}
        )

    jobs_by_token: dict[str, list[Any]] = {}
    for job in jobs:
        token = getattr(job, "source_name_token", None)
        job_id = getattr(job, "job_id", None)
        if not isinstance(token, str) or not isinstance(job_id, str):
            return None
        jobs_by_token.setdefault(token, []).append(job)
    if not set(samples_by_token) <= set(jobs_by_token):
        return None

    validated_segments: list[dict[str, float]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            return None
        start = segment.get("source_start_seconds")
        span = segment.get("duration_seconds")
        if (
            not _valid_number(start)
            or not _valid_number(span, minimum=0.001)
        ):
            return None
        validated_segments.append(
            {
                "source_start_seconds": float(start),
                "duration_seconds": float(span),
            }
        )
    validated_segments.sort(key=lambda segment: segment["source_start_seconds"])
    for left, right in zip(validated_segments, validated_segments[1:]):
        if left["source_start_seconds"] + left["duration_seconds"] > right["source_start_seconds"] + 0.5:
            return None

    links: dict[str, dict[str, Any]] = {}
    for token, samples in samples_by_token.items():
        candidates = jobs_by_token.get(token, [])
        if len(candidates) != 1 or len(samples) < 2:
            return None
        job = candidates[0]
        fps = getattr(job, "fps", 0.0)
        duration = getattr(job, "duration_seconds", 0.0)
        job_id = getattr(job, "job_id", None)
        if (
            not _valid_number(fps, minimum=0.001)
            or not _valid_number(duration, minimum=0.001)
            or not isinstance(job_id, str)
        ):
            return None

        ordered = sorted(samples, key=lambda sample: sample["frame_index"])
        frames = [sample["frame_index"] for sample in ordered]
        times = [sample["eeg_clock_seconds"] for sample in ordered]
        if any(right <= left for left, right in zip(frames, frames[1:])):
            return None
        if any(right <= left for left, right in zip(times, times[1:])):
            return None

        offsets = [time - frame / float(fps) for frame, time in zip(frames, times)]
        source_start = median(offsets)
        if max(abs(offset - source_start) for offset in offsets) > max(0.2, 0.5 / fps):
            return None
        observed_frames = round(float(duration) * float(fps))
        expected_frames = int(max(frames)) + 1
        if abs(observed_frames - expected_frames) > max(10, round(float(fps) * 0.5)):
            return None

        video_end = source_start + float(duration)
        mapped_segments: list[dict[str, float]] = []
        for segment in validated_segments:
            segment_start = segment["source_start_seconds"]
            segment_end = segment_start + segment["duration_seconds"]
            overlap_start = max(source_start, segment_start)
            overlap_end = min(video_end, segment_end)
            if overlap_end <= overlap_start:
                continue
            video_start = overlap_start - source_start
            video_segment_end = overlap_end - source_start
            mapped_segments.append(
                {
                    "video_start_seconds": video_start,
                    "video_end_seconds": video_segment_end,
                    "eeg_source_start_seconds": overlap_start,
                }
            )
        if not mapped_segments:
            return None
        links[job_id] = {
            "eeg_source_start_seconds": source_start,
            "video_duration_seconds": float(duration),
            "eeg_coverage_seconds": sum(
                segment["video_end_seconds"] - segment["video_start_seconds"]
                for segment in mapped_segments
            ),
            "mapped_segments": mapped_segments,
        }
    return links if len(links) == len(samples_by_token) else None


def _recording_manifest(
    db: Session, recording: EEGRecording
) -> dict[str, Any] | None:
    if (
        recording.id is None
        or recording.video_sync_status != "available"
        or recording.video_sync_nonce is None
        or recording.video_sync_ciphertext is None
    ):
        return None
    session = db.get(EEGSession, recording.session_db_id)
    if (
        session is None
        or session.owner_user_id is None
        or not session.case_id
    ):
        return None
    value = decrypt_sync_payload(
        "recording",
        session.owner_user_id,
        session.case_id,
        str(recording.id),
        recording.video_sync_nonce,
        recording.video_sync_ciphertext,
    )
    return value if value is not None else None


def resolve_case_video_sync(
    db: Session,
    owner_user_id: int | None,
    case_id: str | None,
    *,
    acquire_lock: bool = True,
    commit: bool = True,
) -> int:
    """Link complete upload groups to one uniquely matching EEG recording."""

    if owner_user_id is None or not case_id:
        return 0
    if acquire_lock:
        from backend.app.services.case_service import lock_owner_case_mutations

        lock_owner_case_mutations(db, owner_user_id)
    recordings = list(
        db.exec(
            select(EEGRecording)
            .join(EEGSession, EEGRecording.session_db_id == EEGSession.id)
            .where(
                EEGSession.owner_user_id == owner_user_id,
                EEGSession.case_id == case_id,
            )
        ).all()
    )
    jobs = list(
        db.exec(
            select(VideoDetectionJob).where(
                VideoDetectionJob.owner_user_id == owner_user_id,
                VideoDetectionJob.case_id == case_id,
                VideoDetectionJob.source_group_id.is_not(None),
            )
        ).all()
    )
    if not jobs:
        if commit:
            db.commit()
        return 0

    group_jobs: dict[str, list[VideoDetectionJob]] = {}
    for job in jobs:
        if job.source_group_id:
            group_jobs.setdefault(job.source_group_id, []).append(job)

    manifests = {
        recording.id: (recording, _recording_manifest(db, recording))
        for recording in recordings
        if recording.id is not None
    }
    candidates: list[tuple[int, str, dict[str, dict[str, Any]]]] = []
    for recording_id, (_recording, manifest) in manifests.items():
        if manifest is None:
            continue
        for group_id, group in group_jobs.items():
            if not all(job.sync_group_complete for job in group):
                continue
            links = match_sync_video_group(manifest, group)
            if links is not None:
                candidates.append((recording_id, group_id, links))

    by_recording: dict[int, list[tuple[int, str, dict[str, dict[str, Any]]]]] = {}
    by_group: dict[str, list[tuple[int, str, dict[str, dict[str, Any]]]]] = {}
    for candidate in candidates:
        by_recording.setdefault(candidate[0], []).append(candidate)
        by_group.setdefault(candidate[1], []).append(candidate)

    linked_jobs = 0
    for job in jobs:
        job.eeg_recording_db_id = None
        job.eeg_sync_nonce = None
        job.eeg_sync_ciphertext = None
        if not job.sync_group_complete or not recordings:
            job.eeg_sync_status = "pending"
        elif not job.source_name_token:
            job.eeg_sync_status = "unavailable"
        elif not any(manifest is not None for _, manifest in manifests.values()):
            job.eeg_sync_status = "unavailable"
        else:
            job.eeg_sync_status = "unmatched"

        matching = [
            candidate
            for candidate in by_group.get(job.source_group_id or "", [])
            if job.job_id in candidate[2]
        ]
        if len(matching) == 1:
            candidate = matching[0]
            recording_id, _group_id, link_map = candidate
            if len(by_recording[recording_id]) == 1:
                recording = next(
                    recording
                    for recording in recordings
                    if recording.id == recording_id
                )
                session = db.get(EEGSession, recording.session_db_id)
                if session is None or not session.case_id:
                    job.eeg_sync_status = "unavailable"
                else:
                    job.eeg_recording_db_id = recording_id
                    encrypt_job_mapping(
                        job,
                        owner_user_id=owner_user_id,
                        case_id=case_id,
                        mapping=link_map[job.job_id],
                    )
                    job.eeg_sync_status = "linked"
                    linked_jobs += 1
            else:
                job.eeg_sync_status = "ambiguous"
        elif matching:
            job.eeg_sync_status = "ambiguous"
        db.add(job)
    if commit:
        db.commit()
    return linked_jobs
