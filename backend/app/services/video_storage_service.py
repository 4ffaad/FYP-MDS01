"""Private encrypted storage for standalone video privacy jobs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import fcntl
import logging
import math
import os
from pathlib import Path
import re
import stat
import time

from fastapi import UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

from backend.app.core.config import MAX_VIDEO_UPLOAD_BYTES, SESSION_STORAGE_DIR
from backend.app.services.storage_service import SessionStorage, StorageError

PREFLIGHT_ORPHAN_MAX_AGE_SECONDS = 24 * 60 * 60
PLAYBACK_CACHE_IDLE_SECONDS = 10 * 60
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

        return await self._storage.save_chunked_upload(
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
        """Return the encrypted detection review-video path."""

        return self._artifact_path(job_id, "video.visualization.mp4.enc")

    def playback_path(self, job_id: str) -> Path:
        """Return the encrypted VEEG browser-playback copy path."""

        return self._artifact_path(job_id, "video.playback.mp4.enc")

    def work_path(self, job_id: str, name: str) -> Path:
        """Return a safe private plaintext work path."""

        if Path(name).name != name or not name:
            raise StorageError("Video work name is invalid.")
        return self._storage.directory(self._validate_job_id(job_id), "work") / name

    def store_artifact(self, job_id: str, source_path: Path, name: str) -> Path:
        """Encrypt a transformed artifact and remove its plaintext."""

        if name == "video.playback.mp4":
            return self._storage.store_chunked_artifact(
                self._validate_job_id(job_id), source_path, name
            )
        return self._storage.store_encrypted_artifact(self._validate_job_id(job_id), source_path, name)

    def materialize_artifact(self, job_id: str, encrypted_path: Path, name: str) -> Path:
        """Decrypt one retained artifact into temporary private work storage."""

        expected_paths = {
            self.visualization_path(job_id),
            self.playback_path(job_id),
            self._artifact_path(job_id, "predictions.json.enc"),
            self._artifact_path(job_id, "video.output.mp4.enc"),
            self._artifact_path(job_id, "video.preview.jpg.enc"),
        }
        if encrypted_path not in expected_paths:
            raise StorageError("Stored artifact path is not canonical.")
        return self._storage.materialize_retained_artifact(self._validate_job_id(job_id), encrypted_path, name)

    @contextmanager
    def _playback_lock(self, job_id: str) -> Iterator[None]:
        job_root = self.root / self._validate_job_id(job_id)
        if self.root.is_symlink() or job_root.is_symlink() or not job_root.is_dir():
            raise StorageError("Video playback storage is invalid.")
        lock_path = job_root / ".visualization-playback.lock"
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise StorageError("Video playback storage is unavailable.") from exc
        locked = False
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StorageError("Video playback lock is invalid.")
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            locked = True
            yield
        finally:
            if locked:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def visualization_response(self, job_id: str, encrypted_path: Path):
        """Hold a shared storage lease while a browser streams the video."""
        lease = self._storage.read_lease(job_id)
        lease.__enter__()
        try:
            path = self.materialize_visualization_for_playback(job_id, encrypted_path)
        except BaseException:
            lease.__exit__(None, None, None)
            raise
        return CleanupFileResponse(
            path,
            cleanup=lambda: lease.__exit__(None, None, None),
            media_type="video/mp4",
            headers={
                "Cache-Control": "private, no-store, max-age=0",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def source_playback_response(
        self, job_id: str, encrypted_path: Path, range_header: str | None = None
    ):
        """Serve the encrypted original through a private range-capable cache."""

        safe_job_id = self._validate_job_id(job_id)
        expected = self._artifact_path(safe_job_id, "video.input.enc", "original")
        self._require_canonical_path(encrypted_path, expected)
        if self._storage.is_chunked_envelope(expected):
            return self._chunked_playback_response(safe_job_id, expected, range_header)
        lease = self._storage.read_lease(safe_job_id)
        lease.__enter__()
        try:
            path = self._materialize_playback_cache(
                safe_job_id, expected, "source-playback.mp4"
            )
        except BaseException:
            lease.__exit__(None, None, None)
            raise
        return CleanupFileResponse(
            path,
            cleanup=lambda: lease.__exit__(None, None, None),
            media_type="video/mp4",
            headers={
                "Cache-Control": "private, no-store, max-age=0",
                "X-Content-Type-Options": "nosniff",
                "Accept-Ranges": "bytes",
            },
        )

    def reference_playback_response(
        self, job_id: str, encrypted_path: Path, range_header: str | None = None
    ):
        """Serve an encrypted converted VEEG copy through an owner-only cache."""

        safe_job_id = self._validate_job_id(job_id)
        allowed_paths = {self.playback_path(safe_job_id), self.visualization_path(safe_job_id)}
        if encrypted_path not in allowed_paths:
            raise StorageError("Stored playback path is not canonical.")
        if self._storage.is_chunked_envelope(encrypted_path):
            return self._chunked_playback_response(safe_job_id, encrypted_path, range_header)
        lease = self._storage.read_lease(safe_job_id)
        lease.__enter__()
        try:
            path = self._materialize_playback_cache(
                safe_job_id, encrypted_path, "reference-playback-cache.mp4"
            )
        except BaseException:
            lease.__exit__(None, None, None)
            raise
        return CleanupFileResponse(
            path,
            cleanup=lambda: lease.__exit__(None, None, None),
            media_type="video/mp4",
            headers={
                "Cache-Control": "private, no-store, max-age=0",
                "X-Content-Type-Options": "nosniff",
                "Accept-Ranges": "bytes",
            },
        )

    def _chunked_playback_response(
        self, job_id: str, encrypted_path: Path, range_header: str | None
    ):
        """Authenticate and stream only the requested encrypted video chunks."""

        lease = self._storage.read_lease(job_id)
        lease.__enter__()
        try:
            total = self._storage.chunked_plaintext_size(encrypted_path)
            status_code = 200
            start, end = 0, total - 1
            if range_header is not None:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
                if match is None or not any(match.groups()):
                    lease.__exit__(None, None, None)
                    return Response(
                        status_code=416,
                        headers={
                            "Content-Range": f"bytes */{total}",
                            "Cache-Control": "private, no-store, max-age=0",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(int(last), total - 1) if last else total - 1
                else:
                    suffix_length = int(last)
                    if suffix_length <= 0:
                        lease.__exit__(None, None, None)
                        return Response(
                            status_code=416,
                            headers={
                                "Content-Range": f"bytes */{total}",
                                "Cache-Control": "private, no-store, max-age=0",
                                "X-Content-Type-Options": "nosniff",
                            },
                        )
                    start = max(0, total - suffix_length)
                    end = total - 1
                if start >= total or end < start:
                    lease.__exit__(None, None, None)
                    return Response(
                        status_code=416,
                        headers={
                            "Content-Range": f"bytes */{total}",
                            "Cache-Control": "private, no-store, max-age=0",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
                status_code = 206

            headers = {
                "Cache-Control": "private, no-store, max-age=0",
                "X-Content-Type-Options": "nosniff",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
            }
            if status_code == 206:
                headers["Content-Range"] = f"bytes {start}-{end}/{total}"

            def body() -> Iterator[bytes]:
                try:
                    yield from self._storage.iter_decrypted_range(
                        encrypted_path, start, end
                    )
                finally:
                    lease.__exit__(None, None, None)

            return StreamingResponse(
                body(), status_code=status_code, media_type="video/mp4", headers=headers
            )
        except BaseException:
            lease.__exit__(None, None, None)
            raise

    def _materialize_playback_cache(
        self, job_id: str, encrypted_path: Path, cache_name: str
    ) -> Path:
        """Decrypt an approved artifact once for repeated browser range reads."""

        path = self.work_path(job_id, cache_name)
        marker = self.work_path(job_id, f"{cache_name}.ready")
        with self._playback_lock(job_id):
            if path.is_symlink() or marker.is_symlink():
                raise StorageError("Video playback cache is invalid.")
            if path.exists() and marker.is_file():
                if not path.is_file():
                    raise StorageError("Video playback cache is invalid.")
                os.utime(path, None)
                os.utime(marker, None)
                return path
            path.unlink(missing_ok=True)
            marker.unlink(missing_ok=True)
            decrypted = self._storage.materialize_retained_artifact(
                job_id, encrypted_path, cache_name
            )
            descriptor = os.open(
                marker,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.close(descriptor)
            return decrypted

    def materialize_visualization_for_playback(
        self, job_id: str, encrypted_path: Path
    ) -> Path:
        """Decrypt once for efficient range playback, keeping a private idle cache."""

        safe_job_id = self._validate_job_id(job_id)
        expected = self.visualization_path(safe_job_id)
        self._require_canonical_path(encrypted_path, expected)
        path = self.work_path(safe_job_id, "visualization-playback.mp4")
        marker = self.work_path(safe_job_id, "visualization-playback.ready")
        with self._playback_lock(safe_job_id):
            if path.is_symlink() or marker.is_symlink():
                raise StorageError("Video playback cache is invalid.")
            if path.exists() and marker.is_file():
                if not path.is_file():
                    raise StorageError("Video playback cache is invalid.")
                os.utime(path, None)
                os.utime(marker, None)
                return path
            path.unlink(missing_ok=True)
            marker.unlink(missing_ok=True)
            decrypted = self.materialize_artifact(
                safe_job_id, expected, "visualization-playback.mp4"
            )
            descriptor = os.open(
                marker,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.close(descriptor)
            return decrypted

    def cleanup_stale_playback(
        self, job_id: str, *, now: float | None = None
    ) -> None:
        """Remove a decrypted playback cache after ten minutes without access."""

        safe_job_id = self._validate_job_id(job_id)
        work_dir = self.root / safe_job_id / "work"
        if work_dir.is_symlink() or not work_dir.is_dir():
            return
        caches = (
            ("visualization-playback.mp4", "visualization-playback.ready"),
            ("source-playback.mp4", "source-playback.mp4.ready"),
            ("reference-playback-cache.mp4", "reference-playback-cache.mp4.ready"),
        )
        current_time = time.time() if now is None else float(now)
        cutoff = current_time - PLAYBACK_CACHE_IDLE_SECONDS
        with self._playback_lock(safe_job_id):
            for cache_name, marker_name in caches:
                path = work_dir / cache_name
                marker = work_dir / marker_name
                for candidate in (path, marker):
                    if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
                        raise StorageError("Video playback cache is invalid.")
                if (not path.exists()) or path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
                    marker.unlink(missing_ok=True)

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

    def cleanup(
        self,
        job_id: str,
        *,
        keep_retained: bool = True,
        preserve_playback: bool = False,
        keep_original: bool = False,
    ) -> None:
        """Remove original and transient plaintext while retaining ciphertext."""

        preserve = (
            {
                "visualization-playback.mp4",
                "visualization-playback.ready",
                "source-playback.mp4",
                "source-playback.mp4.ready",
                "reference-playback-cache.mp4",
                "reference-playback-cache.mp4.ready",
            }
            if preserve_playback
            else None
        )
        self._storage.cleanup_session(
            self._validate_job_id(job_id),
            keep_retained=keep_retained,
            preserve_work_files=preserve,
            keep_original=keep_original,
        )

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
