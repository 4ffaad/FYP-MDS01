"""Private encrypted storage for standalone video privacy jobs."""

from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse

from backend.app.core.config import MAX_VIDEO_UPLOAD_BYTES, SESSION_STORAGE_DIR
from backend.app.services.storage_service import SessionStorage, StorageError


class CleanupFileResponse(FileResponse):
    """Stream a private plaintext file and always attempt its removal."""

    def __init__(self, path: Path, cleanup: Callable[[], None], **kwargs) -> None:
        super().__init__(path, **kwargs)
        self._cleanup = cleanup

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                self._cleanup()
            except Exception:
                logging.getLogger(__name__).exception("Private video work cleanup failed.")


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

    def materialize_original(
        self, job_id: str, encrypted_path: Path, *, deadline: float | None = None
    ) -> Path:
        """Decrypt the original into a short-lived private work directory."""

        expected = self._artifact_path(job_id, "video.input.enc", "original")
        self._require_canonical_path(encrypted_path, expected)
        return self._storage.materialize_retained_artifact(
            self._validate_job_id(job_id), expected, "video.input", deadline=deadline
        )

    def output_path(self, job_id: str) -> Path:
        """Return the encrypted transformed-output path used internally."""

        return self._artifact_path(job_id, "video.output.mp4.enc")

    def preview_path(self, job_id: str) -> Path:
        """Return the encrypted representative-preview path used internally."""

        return self._artifact_path(job_id, "video.preview.jpg.enc")

    def visualization_path(self, job_id: str) -> Path:
        """Return the encrypted privacy-safe review-video path."""

        return self._artifact_path(job_id, "video.visualization.mp4.enc")

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

        expected_paths = {
            self.visualization_path(job_id),
            self._artifact_path(job_id, "predictions.json.enc"),
            self._artifact_path(job_id, "video.output.mp4.enc"),
            self._artifact_path(job_id, "video.preview.jpg.enc"),
        }
        if encrypted_path not in expected_paths:
            raise StorageError("Stored artifact path is not canonical.")
        return self._storage.materialize_retained_artifact(self._validate_job_id(job_id), encrypted_path, name)

    def _artifact_path(self, job_id: str, filename: str, area: str = "retained") -> Path:
        return self.root / self._validate_job_id(job_id) / area / filename

    @staticmethod
    def _require_canonical_path(value: Path, expected: Path) -> None:
        if value != expected:
            raise StorageError("Stored artifact path is not canonical.")

    def delete_work_file(self, path: Path) -> None:
        """Remove one response-scoped plaintext file without touching peers."""

        job_id = self._validate_job_id(path.parent.parent.name)
        candidate = path.absolute()
        work_root = (self.root / job_id / "work").absolute()
        if work_root.is_symlink() or not work_root.is_dir() or candidate.parent != work_root:
            raise StorageError("Video work path is invalid.")
        if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
            raise StorageError("Video work path is invalid.")
        candidate.unlink(missing_ok=True)

    def cleanup(self, job_id: str, *, keep_retained: bool = True) -> None:
        """Remove original and transient plaintext while retaining ciphertext."""

        self._storage.cleanup_session(self._validate_job_id(job_id), keep_retained=keep_retained)

    def delete_job(self, job_id: str) -> None:
        """Remove all private media for a job."""

        self._storage.delete_session(self._validate_job_id(job_id))
