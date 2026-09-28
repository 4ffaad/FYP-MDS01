"""Encrypted, owner-scoped PDF source reports attached to analysis cases."""

from __future__ import annotations

import os
import re
import secrets
import stat
import time
from pathlib import Path
from typing import Any, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from backend.app.core import config
from backend.app.database.models.case_source_report import CaseSourceReport
from backend.app.privacy.crypto import CryptoError, read_base64_key


SOURCE_REPORT_CRYPTO_VERSION = 1
MAX_CASE_SOURCE_REPORT_BYTES = 25 * 1024 * 1024
_NONCE_BYTES = 12
_TAG_BYTES = 16
_MAGIC = b"MDS01SR1"
_ARTIFACT_ID = re.compile(r"^[a-f0-9]{32}$")
_PDF_HEADER = re.compile(rb"\A%PDF-(?:1\.[0-7]|2\.0)")
_CLEANUP_BATCH_SIZE = 128


class CaseSourceReportError(RuntimeError):
    """Base class for source-report failures safe to map to generic API errors."""


class CaseSourceReportCryptoError(CaseSourceReportError):
    """Raised for unavailable keys, authentication failures, or invalid ciphertext."""


class CaseSourceReportStorageError(CaseSourceReportError):
    """Raised for private storage or database commit failures."""


class InvalidCaseSourceReport(ValueError):
    """Raised when an uploaded or decrypted payload is not a bounded PDF."""


def _associated_data(owner_user_id: int, case_id: str, artifact_id: str, version: int) -> bytes:
    return (
        f"mds01-case-source-report\0{version}\0{owner_user_id}\0{case_id}\0{artifact_id}"
    ).encode("utf-8")


def _report_key(version: int) -> bytes:
    if version != SOURCE_REPORT_CRYPTO_VERSION:
        raise CaseSourceReportCryptoError("Source report is unavailable.")
    try:
        master_key = read_base64_key(config.STORAGE_KEY_ENV)
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"mds01-case-source-report-v{version}".encode("ascii"),
            info=f"case-source-report/v{version}/aes-gcm".encode("ascii"),
        ).derive(master_key)
    except (CryptoError, ValueError) as exc:
        raise CaseSourceReportCryptoError("Source report encryption is unavailable.") from exc


def _validate_pdf(pdf_bytes: bytes) -> None:
    """Reject obvious non-PDF or truncated inputs; this is not a full parser."""

    if not isinstance(pdf_bytes, bytes) or len(pdf_bytes) > MAX_CASE_SOURCE_REPORT_BYTES:
        raise InvalidCaseSourceReport("Source report exceeds the size limit.")
    if not _PDF_HEADER.match(pdf_bytes) or b"%%EOF" not in pdf_bytes[-8192:]:
        raise InvalidCaseSourceReport("Source report must be a PDF.")


def _private_root(*, create: bool) -> Path:
    root = config.STORAGE_DIR / "case-source-reports"
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise CaseSourceReportStorageError("Private report storage is unavailable.")
    if not root.exists():
        if not create:
            return root
        try:
            root.mkdir(parents=True, mode=0o700)
        except OSError as exc:
            raise CaseSourceReportStorageError("Private report storage is unavailable.") from exc
    try:
        os.chmod(root, 0o700)
    except OSError as exc:
        raise CaseSourceReportStorageError("Private report storage is unavailable.") from exc
    return root


def _artifact_path(root: Path, artifact_id: str) -> Path:
    if not _ARTIFACT_ID.fullmatch(artifact_id):
        raise CaseSourceReportStorageError("Private report storage is unavailable.")
    return root / f"{artifact_id}.enc"


def _encrypt_pdf(
    pdf_bytes: bytes,
    *,
    owner_user_id: int,
    case_id: str,
    artifact_id: str,
    version: int,
) -> bytes:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    ciphertext = AESGCM(_report_key(version)).encrypt(
        nonce,
        pdf_bytes,
        _associated_data(owner_user_id, case_id, artifact_id, version),
    )
    return _MAGIC + nonce + ciphertext


def _write_artifact(
    pdf_bytes: bytes,
    *,
    owner_user_id: int,
    case_id: str,
    artifact_id: str,
    version: int,
    replace: bool,
) -> Path:
    root = _private_root(create=True)
    destination = _artifact_path(root, artifact_id)
    if destination.is_symlink() or (destination.exists() and not replace):
        raise CaseSourceReportStorageError("Private report storage is unavailable.")
    encoded = _encrypt_pdf(
        pdf_bytes,
        owner_user_id=owner_user_id,
        case_id=case_id,
        artifact_id=artifact_id,
        version=version,
    )
    temporary = root / f".{secrets.token_hex(16)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CaseSourceReportStorageError("Private report storage is unavailable.") from exc
    return destination


def _remove_artifact(artifact_id: str) -> None:
    root = _private_root(create=False)
    if not root.exists():
        return
    path = _artifact_path(root, artifact_id)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CaseSourceReportStorageError("Private report cleanup failed.") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise CaseSourceReportStorageError("Private report cleanup failed.")
    try:
        path.unlink()
    except OSError as exc:
        raise CaseSourceReportStorageError("Private report cleanup failed.") from exc


def _read_artifact(artifact_id: str) -> bytes:
    root = _private_root(create=False)
    path = _artifact_path(root, artifact_id)
    maximum_stored_size = len(_MAGIC) + _NONCE_BYTES + MAX_CASE_SOURCE_REPORT_BYTES + _TAG_BYTES
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum_stored_size:
            raise CaseSourceReportStorageError("Private source report is unavailable.")
        with path.open("rb") as source:
            encoded = source.read(maximum_stored_size + 1)
    except CaseSourceReportStorageError:
        raise
    except OSError as exc:
        raise CaseSourceReportStorageError("Private source report is unavailable.") from exc
    if len(encoded) > maximum_stored_size:
        raise CaseSourceReportStorageError("Private source report is unavailable.")
    if len(encoded) < len(_MAGIC) + _NONCE_BYTES + _TAG_BYTES or not encoded.startswith(_MAGIC):
        raise CaseSourceReportCryptoError("Source report is unavailable.")
    return encoded


def _decrypt_pdf(
    encoded: bytes,
    *,
    owner_user_id: int,
    case_id: str,
    artifact_id: str,
    version: int,
) -> bytes:
    nonce_start = len(_MAGIC)
    nonce = encoded[nonce_start : nonce_start + _NONCE_BYTES]
    ciphertext = encoded[nonce_start + _NONCE_BYTES :]
    try:
        pdf_bytes = AESGCM(_report_key(version)).decrypt(
            nonce,
            ciphertext,
            _associated_data(owner_user_id, case_id, artifact_id, version),
        )
    except (InvalidTag, ValueError) as exc:
        raise CaseSourceReportCryptoError("Source report is unavailable.") from exc
    try:
        _validate_pdf(pdf_bytes)
    except InvalidCaseSourceReport as exc:
        raise CaseSourceReportCryptoError("Source report is unavailable.") from exc
    return pdf_bytes


def _find_report(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
    for_update: bool = False,
) -> CaseSourceReport | None:
    statement = select(CaseSourceReport).where(
        CaseSourceReport.case_id == case_id,
        CaseSourceReport.owner_user_id == owner_user_id,
    )
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return db.exec(statement).first()


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise CaseSourceReportStorageError("Source report storage is unavailable.") from exc


def _settle_cleanup_pointer(db: Session, row: CaseSourceReport) -> None:
    locked_row = _find_report(
        db,
        case_id=row.case_id,
        owner_user_id=row.owner_user_id,
        for_update=True,
    )
    if locked_row is None:
        return
    row = locked_row
    artifact_id = row.cleanup_artifact_id
    if artifact_id is None:
        return
    _remove_artifact(artifact_id)
    if row.artifact_id is None:
        db.delete(row)
    else:
        row.cleanup_artifact_id = None
        db.add(row)
    _commit(db)


def save_case_source_report(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
    pdf_bytes: bytes,
) -> None:
    """Atomically write an encrypted PDF and persist only its opaque pointer."""

    _validate_pdf(pdf_bytes)
    row = _find_report(
        db,
        case_id=case_id,
        owner_user_id=owner_user_id,
        for_update=True,
    )
    if row is not None and row.cleanup_artifact_id is not None:
        _settle_cleanup_pointer(db, row)
        row = _find_report(
            db,
            case_id=case_id,
            owner_user_id=owner_user_id,
            for_update=True,
        )

    if row is not None and row.artifact_id is not None:
        if row.crypto_version != SOURCE_REPORT_CRYPTO_VERSION:
            raise CaseSourceReportCryptoError("Source report is unavailable.")
        try:
            _write_artifact(
                pdf_bytes,
                owner_user_id=owner_user_id,
                case_id=case_id,
                artifact_id=row.artifact_id,
                version=row.crypto_version,
                replace=True,
            )
        finally:
            # Release the row lock before returning. The pointer is unchanged,
            # so the replacement has no SQL mutation to commit.
            db.rollback()
        return

    artifact_id = secrets.token_hex(16)
    _write_artifact(
        pdf_bytes,
        owner_user_id=owner_user_id,
        case_id=case_id,
        artifact_id=artifact_id,
        version=SOURCE_REPORT_CRYPTO_VERSION,
        replace=False,
    )
    row = CaseSourceReport(
        case_id=case_id,
        owner_user_id=owner_user_id,
        artifact_id=artifact_id,
        crypto_version=SOURCE_REPORT_CRYPTO_VERSION,
    )
    db.add(row)
    try:
        _commit(db)
    except CaseSourceReportStorageError as commit_error:
        try:
            persisted = _find_report(db, case_id=case_id, owner_user_id=owner_user_id)
        except Exception:
            # A lost connection leaves the transaction outcome unknown. Keep
            # the authenticated ciphertext rather than risk deleting a file
            # that a committed pointer now references.
            raise commit_error
        if (
            persisted is not None
            and persisted.artifact_id == artifact_id
            and persisted.crypto_version == SOURCE_REPORT_CRYPTO_VERSION
        ):
            return
        try:
            _remove_artifact(artifact_id)
        except CaseSourceReportStorageError:
            pass
        raise commit_error


def load_case_source_report(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
) -> bytes | None:
    """Load and authenticate only the requesting owner's case PDF."""

    row = _find_report(db, case_id=case_id, owner_user_id=owner_user_id)
    if row is None:
        return None
    if row.cleanup_artifact_id is not None:
        _settle_cleanup_pointer(db, row)
        row = _find_report(db, case_id=case_id, owner_user_id=owner_user_id)
        if row is None:
            return None
    if row.artifact_id is None:
        return None
    return _decrypt_pdf(
        _read_artifact(row.artifact_id),
        owner_user_id=owner_user_id,
        case_id=case_id,
        artifact_id=row.artifact_id,
        version=row.crypto_version,
    )


def stage_case_source_report_cleanup(
    db: Session,
    *,
    case_id: str,
    owner_user_id: int,
) -> bool:
    """Stage a durable tombstone in the caller's current transaction.

    The caller must commit this transaction before attempting physical file
    removal. Until commit, the active pointer remains visible to other
    transactions; after commit, report reads cannot serve the artifact and
    the cleanup sweep can finish an interrupted deletion.
    """

    row = _find_report(
        db,
        case_id=case_id,
        owner_user_id=owner_user_id,
        for_update=True,
    )
    if row is None:
        return False

    # A prior failed cleanup can coexist with a newly active pointer only if
    # the row was written by older or interrupted code. Retire the old,
    # already-inactive artifact before reusing the single cleanup slot.
    if row.cleanup_artifact_id is not None and row.artifact_id is not None:
        _remove_artifact(row.cleanup_artifact_id)
        row.cleanup_artifact_id = None

    if row.artifact_id is not None:
        row.cleanup_artifact_id = row.artifact_id
        row.artifact_id = None
        db.add(row)
    return True


def delete_case_source_report(db: Session, *, case_id: str, owner_user_id: int) -> bool:
    """Delete the PDF without dropping its cleanup pointer before file removal."""

    row = _find_report(
        db,
        case_id=case_id,
        owner_user_id=owner_user_id,
        for_update=True,
    )
    if row is None:
        return False
    if row.cleanup_artifact_id is not None:
        _settle_cleanup_pointer(db, row)
        row = _find_report(
            db,
            case_id=case_id,
            owner_user_id=owner_user_id,
            for_update=True,
        )
        if row is None:
            return True
    if row.artifact_id is not None:
        row.cleanup_artifact_id = row.artifact_id
        row.artifact_id = None
        db.add(row)
        _commit(db)
    if row.cleanup_artifact_id is not None:
        _settle_cleanup_pointer(db, row)
    return True


def cleanup_orphaned_case_source_reports(
    db: Session,
    *,
    older_than_seconds: float = 3600,
) -> None:
    """Retry tombstone cleanup and age out unreferenced ciphertext in bounded batches."""

    if older_than_seconds < 0:
        raise ValueError("Cleanup age must be non-negative.")

    case_column = cast(Any, CaseSourceReport.case_id)
    cleanup_column = cast(Any, CaseSourceReport.cleanup_artifact_id)
    owner_column = cast(Any, CaseSourceReport.owner_user_id)
    last_key: tuple[str, int] | None = None
    while True:
        statement = (
            select(CaseSourceReport)
            .where(cleanup_column.is_not(None))
            .order_by(case_column, owner_column)
            .limit(_CLEANUP_BATCH_SIZE)
        )
        if last_key is not None:
            last_case_id, last_owner_user_id = last_key
            statement = statement.where(
                or_(
                    case_column > last_case_id,
                    and_(
                        case_column == last_case_id,
                        owner_column > last_owner_user_id,
                    ),
                )
            )
        rows = list(db.exec(statement).all())
        if not rows:
            break
        for row in rows:
            last_key = (row.case_id, row.owner_user_id)
            try:
                _settle_cleanup_pointer(db, row)
            except CaseSourceReportError:
                # Keep the SQL pointer so a later sweep can safely retry deletion.
                continue

    root = _private_root(create=False)
    if not root.exists():
        return

    cutoff = time.time() - older_than_seconds
    artifact_batch: list[tuple[str, Any]] = []
    artifact_column = cast(Any, CaseSourceReport.artifact_id)

    def cleanup_artifact_batch() -> None:
        if not artifact_batch:
            return
        artifact_ids = [artifact_id for artifact_id, _entry in artifact_batch]
        reference_rows = db.exec(
            select(artifact_column, cleanup_column).where(
                or_(
                    artifact_column.in_(artifact_ids),
                    cleanup_column.in_(artifact_ids),
                )
            )
        ).all()
        referenced_ids = {
            artifact_id
            for row in reference_rows
            for artifact_id in row
            if artifact_id is not None
        }
        for artifact_id, _entry in artifact_batch:
            if artifact_id not in referenced_ids:
                _remove_artifact(artifact_id)
        artifact_batch.clear()

    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    metadata = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_mtime > cutoff:
                    continue

                artifact_match = re.fullmatch(r"([a-f0-9]{32})\.enc", entry.name)
                if artifact_match is not None:
                    artifact_batch.append((artifact_match.group(1), entry))
                    if len(artifact_batch) >= _CLEANUP_BATCH_SIZE:
                        cleanup_artifact_batch()
                    continue

                if re.fullmatch(r"\.[a-f0-9]{32}\.tmp", entry.name):
                    try:
                        Path(entry.path).unlink()
                    except FileNotFoundError:
                        continue
                    except OSError as exc:
                        raise CaseSourceReportStorageError(
                            "Private report cleanup failed."
                        ) from exc
            cleanup_artifact_batch()
    except OSError as exc:
        raise CaseSourceReportStorageError("Private report cleanup failed.") from exc
