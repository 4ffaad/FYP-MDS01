"""Batch endpoints for an EEG session delivered as one ZIP archive.

HTTP uploads cannot preserve a local folder by themselves. The client uploads
one ZIP containing (for example) a ``chb01/`` directory with many EDF files.
Each EDF becomes one database recording, while the ZIP becomes one session.
"""

from pathlib import Path
import re
import shutil
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.config import DEIDENTIFIED_DIR, INCOMING_DIR, PROJECT_ROOT, ensure_storage_directories
from app.database.db import get_session
from app.models.eeg import EEGRecording, EEGSession, RecordingStatus
from app.services.deidentification import deidentify_edf, generate_record_id, inspect_metadata
from app.services.preprocessing import preprocess_edf_to_npz


router = APIRouter(prefix="/api/v1", tags=["EEG pipeline"])
MAX_EDF_FILES_PER_ARCHIVE = 500


def _new_session_id() -> str:
    """Create an opaque identifier for one uploaded folder/archive."""
    return f"SES-{uuid.uuid4().hex[:8].upper()}"


def _natural_sort_key(path: zipfile.ZipInfo) -> list[object]:
    """Sort chb01_2.edf before chb01_10.edf rather than lexicographically."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.filename)]


def _public_record(record: EEGRecording, session_id: str) -> dict:
    """Build an API-safe record summary without the patient reference."""
    return {
        "record_id": record.record_id,
        "session_id": session_id,
        "sequence_index": record.sequence_index,
        "status": record.status,
        "source_filename": record.original_filename,
        "duration_seconds": record.duration_seconds,
        "sampling_rate": record.sampling_rate,
        "channel_count": record.channel_count,
        "deidentified_file": Path(record.deidentified_path).name if record.deidentified_path else None,
        "preprocessed_file": Path(record.preprocessed_path).name if record.preprocessed_path else None,
        "error_message": record.error_message,
    }


def _edf_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Return regular EDF members in predictable numeric filename order."""
    members = [
        member for member in archive.infolist()
        if not member.is_dir() and Path(member.filename).suffix.lower() == ".edf"
    ]
    if not members:
        raise ValueError("ZIP archive does not contain any EDF files.")
    if len(members) > MAX_EDF_FILES_PER_ARCHIVE:
        raise ValueError(f"ZIP archive contains more than {MAX_EDF_FILES_PER_ARCHIVE} EDF files.")
    return sorted(members, key=_natural_sort_key)


@router.post("/deidentify", status_code=201)
async def deidentify_eeg_archive(
    archive: UploadFile = File(...),
    patient_reference: str = Form(...),
    db: Session = Depends(get_session),
):
    """De-identify every EDF in one uploaded session ZIP.

    The ZIP may contain nested folders such as ``chb01/chb01_01.edf``. Files
    are read directly from the archive one at a time, so the server does not
    extract the whole archive before processing. The original patient reference
    is stored only in SQLite; generated EDF files contain only ``REC-*`` IDs.
    """
    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload one ZIP archive containing EDF files.")
    if not patient_reference.strip():
        raise HTTPException(status_code=400, detail="patient_reference is required.")

    try:
        zip_file = zipfile.ZipFile(archive.file)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive.") from exc

    try:
        members = _edf_members(zip_file)
    except ValueError as exc:
        zip_file.close()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    eeg_session = EEGSession(
        session_id=_new_session_id(), patient_reference=patient_reference.strip()
    )
    db.add(eeg_session)
    db.commit()
    db.refresh(eeg_session)
    ensure_storage_directories()

    records: list[EEGRecording] = []
    try:
        for sequence_index, member in enumerate(members, start=1):
            record = EEGRecording(
                record_id=generate_record_id(),
                session_db_id=eeg_session.id,
                sequence_index=sequence_index,
                original_filename=Path(member.filename).name,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            input_path = INCOMING_DIR / f"{uuid.uuid4().hex}.edf"
            output_path = DEIDENTIFIED_DIR / f"{record.record_id}.edf"
            try:
                with zip_file.open(member) as source, input_path.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                metadata = inspect_metadata(input_path)
                deidentify_edf(input_path, output_path, record.record_id)

                technical = metadata["technical"]
                record.deidentified_path = str(output_path.relative_to(PROJECT_ROOT))
                record.duration_seconds = technical["duration_seconds"]
                record.sampling_rate = int(technical["sampling_frequencies_hz"][0])
                record.channel_count = technical["number_of_channels"]
                record.status = RecordingStatus.DEIDENTIFIED
            except Exception as exc:
                record.status = RecordingStatus.FAILED
                record.error_message = str(exc)
            finally:
                input_path.unlink(missing_ok=True)

            db.add(record)
            db.commit()
            db.refresh(record)
            records.append(record)
    finally:
        zip_file.close()

    completed = sum(record.status == RecordingStatus.DEIDENTIFIED for record in records)
    return {
        "session_id": eeg_session.session_id,
        "summary": {
            "edf_files_found": len(members),
            "deidentified": completed,
            "failed": len(records) - completed,
        },
        "records": [_public_record(record, eeg_session.session_id) for record in records],
    }


@router.post("/preprocess/{session_id}")
def preprocess_eeg_session(session_id: str, db: Session = Depends(get_session)):
    """Create model-ready NPZ files for all de-identified EDFs in a session.

    Each variable-duration EDF becomes its own model artifact. A one-hour EDF
    produces many four-second windows, while a ten-minute EDF produces fewer;
    no files are merged and no model input is returned as huge JSON data.
    """
    eeg_session = db.exec(
        select(EEGSession).where(EEGSession.session_id == session_id)
    ).first()
    if eeg_session is None:
        raise HTTPException(status_code=404, detail="EEG session was not found.")

    records = db.exec(
        select(EEGRecording)
        .where(EEGRecording.session_db_id == eeg_session.id)
        .order_by(EEGRecording.sequence_index)
    ).all()
    if not records:
        raise HTTPException(status_code=409, detail="This session has no EDF recordings.")

    results = []
    for record in records:
        if record.status not in {RecordingStatus.DEIDENTIFIED, RecordingStatus.PROCESSED}:
            results.append({"record": _public_record(record, session_id), "model_input": None})
            continue
        if not record.deidentified_path:
            record.status = RecordingStatus.FAILED
            record.error_message = "No deidentified EDF is linked to this record."
            db.add(record)
            db.commit()
            results.append({"record": _public_record(record, session_id), "model_input": None})
            continue

        input_path = PROJECT_ROOT / record.deidentified_path
        try:
            record.status = RecordingStatus.PROCESSING
            record.error_message = None
            db.add(record)
            db.commit()

            output_path, details = preprocess_edf_to_npz(input_path, record.record_id)
            record.preprocessed_path = str(output_path.relative_to(PROJECT_ROOT))
            record.status = RecordingStatus.PROCESSED
            db.add(record)
            db.commit()
            db.refresh(record)
            results.append({
                "record": _public_record(record, session_id),
                "model_input": {
                    "format": "npz",
                    "path": record.preprocessed_path,
                    "arrays": ["model_windows", "window_start_seconds", "sampling_rate", "channel_labels"],
                    "shape": details["model_input_shape"],
                    "dtype": "float32",
                },
                **details,
            })
        except Exception as exc:
            record.status = RecordingStatus.FAILED
            record.error_message = str(exc)
            db.add(record)
            db.commit()
            results.append({"record": _public_record(record, session_id), "model_input": None})

    processed = sum(item["record"]["status"] == RecordingStatus.PROCESSED for item in results)
    return {
        "session_id": session_id,
        "summary": {"processed": processed, "failed_or_skipped": len(results) - processed},
        "records": results,
    }
