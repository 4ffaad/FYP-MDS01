"""Response-scoped plaintext for protected original downloads."""
from pathlib import Path
import secrets

from backend.app.services.storage_service import SessionStorage, StorageError
from backend.app.services.video_storage_service import CleanupFileResponse


def original_response(storage: SessionStorage, session_id: str, encrypted: Path, filename: str):
    lease = storage.read_lease(session_id)
    lease.__enter__()
    try:
        path = storage.materialize_retained_artifact(session_id, encrypted, f"download-{secrets.token_hex(16)}")
    except BaseException:
        lease.__exit__(None, None, None)
        raise
    def cleanup():
        try:
            path.unlink(missing_ok=True)
        finally:
            lease.__exit__(None, None, None)
    return CleanupFileResponse(
        path, cleanup=cleanup, filename=filename,
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, no-store, max-age=0", "X-Content-Type-Options": "nosniff"},
    )


def source_report_response(storage, session):
    from fastapi.responses import Response
    with storage.read_lease(session.session_id):
        archive_path = storage.materialize_retained_artifact(
            session.session_id, Path(session.original_path), f"report-{secrets.token_hex(16)}.zip"
        )
        try:
            with storage._open_bounded_zip(archive_path) as archive:
                members = [member for member in storage._validated_archive_members(archive)
                           if member.filename in {"source-report.doc", "source-report.docx", "source-report.pdf"}]
                if len(members) != 1 or members[0].file_size > 25 * 1024 * 1024:
                    raise StorageError("Original report is unavailable.")
                member = members[0]
                payload = archive.read(member)
            return Response(payload, media_type="application/octet-stream", headers={
                "Content-Disposition": f'attachment; filename="{member.filename}"',
                "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"
            })
        finally:
            archive_path.unlink(missing_ok=True)
