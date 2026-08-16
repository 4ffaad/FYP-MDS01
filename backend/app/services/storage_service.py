"""Safe session-scoped filesystem storage."""

from __future__ import annotations

import shutil
import re
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from backend.app.core.config import (
    MAX_ARCHIVE_MEMBER_BYTES,
    MAX_EDF_FILES_PER_ARCHIVE,
    MAX_UPLOAD_BYTES,
    SESSION_STORAGE_DIR,
)


class StorageError(ValueError):
    """Raised when an archive or storage operation is unsafe."""


class SessionStorage:
    """Manage files for one opaque analysis session."""

    def __init__(self, root: Path = SESSION_STORAGE_DIR) -> None:
        self.root = root

    def session_dir(self, session_id: str) -> Path:
        path = self.root / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def directory(self, session_id: str, name: str) -> Path:
        if name not in {"original", "extracted", "deidentified", "processed", "explanations"}:
            raise StorageError("Unknown session storage area.")
        path = self.session_dir(session_id) / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save_upload(self, session_id: str, upload: UploadFile) -> Path:
        if not upload.filename:
            raise StorageError("Uploaded archive has no filename.")
        destination = self.directory(session_id, "original") / "upload.zip"
        total = 0
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    destination.unlink(missing_ok=True)
                    raise StorageError("Uploaded archive exceeds the size limit.")
                output.write(chunk)
        return destination

    def save_archive_bytes(self, session_id: str, filename: str, data: bytes) -> Path:
        if len(data) > MAX_UPLOAD_BYTES:
            raise StorageError("Uploaded archive exceeds the size limit.")
        destination = self.directory(session_id, "original") / "upload.zip"
        destination.write_bytes(data)
        return destination

    @staticmethod
    def _safe_member_path(member_name: str) -> PurePosixPath:
        member_name = member_name.replace("\\", "/")
        candidate = PurePosixPath(member_name)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise StorageError("Archive contains an unsafe path.")
        if not candidate.name:
            raise StorageError("Archive contains an invalid file path.")
        return candidate

    def extract_edfs(self, session_id: str, archive_path: Path) -> list[Path]:
        extracted_dir = self.directory(session_id, "extracted")
        with zipfile.ZipFile(archive_path) as archive:
            members = [
                member
                for member in archive.infolist()
                if not member.is_dir() and Path(member.filename).suffix.lower() == ".edf"
            ]
            if not members:
                raise StorageError("ZIP archive does not contain EDF files.")
            if len(members) > MAX_EDF_FILES_PER_ARCHIVE:
                raise StorageError("ZIP archive contains too many EDF files.")

            outputs: list[Path] = []
            used_names: set[str] = set()
            natural_key = lambda item: [
                int(part) if part.isdigit() else part.lower()
                for part in re.split(r"(\d+)", item.filename)
            ]
            for member in sorted(members, key=natural_key):
                relative = self._safe_member_path(member.filename)
                if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise StorageError("Archive member exceeds the size limit.")
                # Store only the basename to prevent user-controlled directory
                # layouts from escaping the session boundary.
                destination = extracted_dir / relative.name
                if destination.name in used_names:
                    raise StorageError("Archive contains duplicate EDF filenames.")
                used_names.add(destination.name)
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
                outputs.append(destination)
            return outputs

    def deidentified_path(self, session_id: str, record_id: str) -> Path:
        return self.directory(session_id, "deidentified") / f"{record_id}.edf"

    def processed_path(self, session_id: str, record_id: str) -> Path:
        return self.directory(session_id, "processed") / f"{record_id}.npz"

    def explanation_path(self, session_id: str, prediction_id: int) -> Path:
        return self.directory(session_id, "explanations") / f"prediction-{prediction_id}.json"
