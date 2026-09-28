"""Private encrypted storage for standalone video privacy jobs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import fcntl
import logging
import math
import os
from pathlib import Path
import stat
import time

from fastapi import UploadFile
from fastapi.responses import FileResponse

from backend.app.core.config import MAX_VIDEO_UPLOAD_BYTES, SESSION_STORAGE_DIR
from backend.app.services.storage_service import SessionStorage, StorageError

PREFLIGHT_ORPHAN_MAX_AGE_SECONDS = 24 * 60 * 60
PREFLIGHT_PREFIX = "VID-PREFLIGHT-"


def _is_preflight_job_id(job_id: str) -> bool:
    suffix = job_id.removeprefix(PREFLIGHT_PREFIX)
    return (
        job_id.startswith(PREFLIGHT_PREFIX)
        and len(suffix) == 24
        and all(character in "0123456789ABCDEF" for character in suffix)
    )


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
        """Return the legacy encrypted detection-visualization path."""

        return self._artifact_path(job_id, "video.visualization.mp4.enc")

    def delete_legacy_visualization(self, job_id: str, encrypted_path: Path) -> None:
        """Remove only the canonical legacy detection visualization artifact."""

        expected = self.visualization_path(job_id)
        self._require_canonical_path(encrypted_path, expected)
        job_dir = self.root / self._validate_job_id(job_id)
        retained_dir = job_dir / "retained"
        if self.root.is_symlink() or job_dir.is_symlink() or retained_dir.is_symlink():
            raise StorageError("Stored artifact path is not canonical.")
        if not retained_dir.exists():
            return
        if not retained_dir.is_dir():
            raise StorageError("Stored artifact path is not canonical.")
        if expected.is_symlink() or (expected.exists() and not expected.is_file()):
            raise StorageError("Stored artifact path is not canonical.")
        expected.unlink(missing_ok=True)

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

    @contextmanager
    def preflight_upload_lease(self, job_id: str) -> Iterator[None]:
        """Hold an OS-level lease so cleanup workers cannot remove active uploads."""

        if not _is_preflight_job_id(job_id):
            raise StorageError("Video preflight identifier is invalid.")
        job_root = self._storage.session_dir(job_id)
        lock_path = job_root / ".preflight.lock"
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise StorageError("Video preflight lease is unavailable.") from exc

        locked = False
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StorageError("Video preflight lease is invalid.")
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            except OSError as exc:
                raise StorageError("Video preflight lease is unavailable.") from exc
            locked = True
            yield
        finally:
            if locked:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError:
                    logging.getLogger(__name__).warning("Video preflight lease release was delayed.")
            os.close(descriptor)

    def cleanup_stale_preflight_uploads(
        self,
        *,
        max_age_seconds: float = PREFLIGHT_ORPHAN_MAX_AGE_SECONDS,
        now: float | None = None,
    ) -> int:
        """Remove only old, opaque standalone-preflight upload directories."""

        max_age = float(max_age_seconds)
        current_time = time.time() if now is None else float(now)
        if not math.isfinite(max_age) or max_age <= 0 or not math.isfinite(current_time):
            raise ValueError("Preflight orphan age must be finite and positive.")
        root = self.root
        if root.is_symlink() or not root.is_dir():
            return 0
        cutoff = current_time - max_age
        try:
            candidates = list(root.iterdir())
        except OSError:
            logging.getLogger(__name__).warning("Stale video preflight scan unavailable.")
            return 0

        removed = 0
        for candidate in candidates:
            if not _is_preflight_job_id(candidate.name):
                continue
            descriptor: int | None = None
            locked = False
            try:
                info = candidate.lstat()
                if candidate.is_symlink() or not stat.S_ISDIR(info.st_mode):
                    continue

                lock_path = candidate / ".preflight.lock"
                flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                try:
                    descriptor = os.open(lock_path, flags | os.O_CREAT | os.O_EXCL, 0o600)
                    created_lock = True
                except FileExistsError:
                    descriptor = os.open(lock_path, flags)
                    created_lock = False
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    continue
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                locked = True

                current_info = candidate.lstat()
                if (
                    candidate.is_symlink()
                    or not stat.S_ISDIR(current_info.st_mode)
                    or (current_info.st_dev, current_info.st_ino) != (info.st_dev, info.st_ino)
                ):
                    continue
                last_activity = info.st_mtime
                for descendant in candidate.rglob("*"):
                    if created_lock and descendant == lock_path:
                        continue
                    last_activity = max(last_activity, descendant.lstat().st_mtime)
                if last_activity >= cutoff:
                    continue
                self.delete_job(candidate.name)
                removed += 1
            except (OSError, StorageError):
                logging.getLogger(__name__).warning(
                    "Stale video preflight cleanup unavailable; retrying next sweep."
                )
            finally:
                if descriptor is not None:
                    if locked:
                        try:
                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                        except OSError:
                            logging.getLogger(__name__).warning(
                                "Stale video preflight lease release was delayed."
                            )
                    os.close(descriptor)
        return removed
