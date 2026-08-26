"""Private encrypted storage for standalone video privacy jobs."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from backend.app.core.config import MAX_VIDEO_UPLOAD_BYTES, SESSION_STORAGE_DIR
from backend.app.services.storage_service import SessionStorage, StorageError


class VideoStorage:
    """Keep video media below the same owner-only session root as EEG files.

    The service deliberately exposes paths only to other backend services. API
    serializers receive no instance of this class and therefore cannot leak a
    filesystem location accidentally.
    """

    def __init__(self, root: Path = SESSION_STORAGE_DIR, storage_key: bytes | None = None) -> None:
        self._storage = SessionStorage(root=root, storage_key=storage_key)

    @property
    def root(self) -> Path:
        """Return the private storage root for internal cleanup checks."""

        return self._storage.root

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        if not job_id.startswith("VID-") or Path(job_id).name != job_id:
            raise StorageError("Video job identifier is invalid.")
        return job_id

    async def save_upload(self, job_id: str, upload: UploadFile) -> Path:
        """Encrypt the incoming media before it reaches the processor."""

        return await self._storage.save_upload(
            self._validate_job_id(job_id),
            upload,
            max_bytes=MAX_VIDEO_UPLOAD_BYTES,
            filename="video.input.enc",
        )

    def materialize_original(self, job_id: str, encrypted_path: Path) -> Path:
        """Decrypt the original into a short-lived private work directory."""

        return self._storage.materialize_retained_artifact(
            self._validate_job_id(job_id), encrypted_path, "video.input"
        )

    def output_path(self, job_id: str) -> Path:
        """Return the encrypted transformed-output path used internally."""

        return self._storage.directory(self._validate_job_id(job_id), "retained") / "video.output.mp4.enc"

    def preview_path(self, job_id: str) -> Path:
        """Return the encrypted representative-preview path used internally."""

        return self._storage.directory(self._validate_job_id(job_id), "retained") / "video.preview.jpg.enc"

    def work_path(self, job_id: str, name: str) -> Path:
        """Return a safe private plaintext work path."""

        if Path(name).name != name or not name:
            raise StorageError("Video work name is invalid.")
        return self._storage.directory(self._validate_job_id(job_id), "work") / name

    def store_artifact(self, job_id: str, source_path: Path, name: str) -> Path:
        """Encrypt a transformed artifact and remove its plaintext."""

        return self._storage.store_encrypted_artifact(self._validate_job_id(job_id), source_path, name)

    def materialize_artifact(self, job_id: str, encrypted_path: Path, name: str) -> Path:
        """Decrypt one retained artifact into temporary private work storage."""

        return self._storage.materialize_retained_artifact(
            self._validate_job_id(job_id), encrypted_path, name
        )

    def delete_work_file(self, path: Path) -> None:
        """Remove one response-scoped plaintext file without touching peers."""

        candidate = path.resolve()
        work_root = (self.root / path.parent.parent.name / "work").resolve()
        if work_root not in candidate.parents:
            raise StorageError("Video work path is invalid.")
        candidate.unlink(missing_ok=True)

    def cleanup(self, job_id: str, *, keep_retained: bool = True) -> None:
        """Remove original and transient plaintext while retaining ciphertext."""

        self._storage.cleanup_session(self._validate_job_id(job_id), keep_retained=keep_retained)

    def delete_job(self, job_id: str) -> None:
        """Remove all private media for a job."""

        self._storage.delete_session(self._validate_job_id(job_id))
