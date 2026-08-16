"""
EEG batch ingestion and preprocessing API.

This module handles the first two stages of the EEG processing pipeline:

    1. Upload a ZIP archive containing one or more EDF files.
    2. Create a database session representing the patient's recording session.
    3. Create a database record for each EDF file.
    4. De-identify each EDF file.
    5. Store only the de-identified EDF path in the recording record.
    6. Preprocess the de-identified EDF files into model-ready NPZ files.

High-level architecture:

    Frontend
       │
       │ ZIP + patient_reference
       ▼
    POST /api/v1/deidentify
       │
       ├── EEGSession
       │      └── patient_reference  ← restricted / backend only
       │
       ├── EEGRecording
       │      ├── REC-XXXX
       │      └── deidentified_path
       │
       ▼
    De-identified EDF
       │
       ▼
    POST /api/v1/preprocess/{session_id}
       │
       ▼
    Preprocessed NPZ
       │
       ▼
    Model
       │
       ▼
    EEGWindowResult
       │
       ▼
    Frontend
"""

from pathlib import Path
import re
import shutil
import uuid
import zipfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlmodel import Session, select

from backend.app.core.config import (
    DEIDENTIFIED_DIR,
    INCOMING_DIR,
    PROJECT_ROOT,
    ensure_storage_directories,
)

from backend.app.database.db import get_session

from backend.app.models.eeg import (
    EEGRecording,
    EEGSession,
    RecordingStatus,
)

from backend.app.services.deidentification import (
    deidentify_edf,
    generate_record_id,
    inspect_metadata,
)

from backend.app.services.preprocessing import (
    preprocess_edf_to_npz,
)


# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(
    prefix="/api/v1",
    tags=["EEG pipeline"],
)


# Maximum number of EDF files allowed in a single uploaded ZIP.
#
# This prevents someone from accidentally or intentionally uploading an
# extremely large archive containing thousands of EEG recordings.
MAX_EDF_FILES_PER_ARCHIVE = 500


# ============================================================================
# SESSION ID GENERATION
# ============================================================================

def _new_session_id() -> str:
    """
    Generate an opaque identifier for one EEG upload session.

    A session represents a collection of EDF files belonging to the same
    patient recording/session.

    Example:

        SES-7A31F2C9

    This identifier does NOT contain the patient's name, hospital ID,
    filename, or other patient-identifying information.

    Returns
    -------
    str
        A unique session identifier beginning with ``SES-``.
    """

    return f"SES-{uuid.uuid4().hex[:8].upper()}"


# ============================================================================
# API RESPONSE SERIALIZATION
# ============================================================================

def _public_record(
    record: EEGRecording,
    session_id: str,
) -> dict:
    """
    Convert an EEGRecording database object into a safe API response.

    The database contains some restricted information, such as the
    patient's clinical reference. That information must NOT be returned
    to the frontend as part of normal EEG processing responses.

    This function therefore exposes only information required by the
    frontend to track the processing pipeline.

    Parameters
    ----------
    record : EEGRecording
        Database record representing one EDF file.

    session_id : str
        Public session identifier associated with the recording.

    Returns
    -------
    dict
        JSON-serializable representation of the recording.

    Example response:

        {
            "record_id": "REC-A91F23BC",
            "session_id": "SES-7A31F2C9",
            "sequence_index": 1,
            "status": "deidentified",
            ...
        }

    Note
    ----
    ``patient_reference`` is intentionally NOT included.
    """

    return {
        "record_id": record.record_id,
        "session_id": session_id,
        "sequence_index": record.sequence_index,
        "status": record.status,
        # Submitted filenames can contain patient identifiers. The legacy
        # response keeps its field for compatibility but returns a generated
        # display name instead.
        "source_filename": f"recording_{record.sequence_index:02d}.edf",
        "duration_seconds": record.duration_seconds,
        "sampling_rate": record.sampling_rate,
        "channel_count": record.channel_count,

        # Only return the filename rather than the complete server path.
        "deidentified_file": (
            Path(record.deidentified_path).name
            if record.deidentified_path
            else None
        ),

        "preprocessed_file": (
            Path(record.preprocessed_path).name
            if record.preprocessed_path
            else None
        ),

        "error_message": record.error_message,
    }


# ============================================================================
# ZIP / EDF DISCOVERY
# ============================================================================

def _natural_sort_key(
    path: zipfile.ZipInfo,
) -> list[object]:
    """
    Generate a natural sorting key for a ZIP member filename.

    Normal alphabetical sorting would produce:

        chb01_1.edf
        chb01_10.edf
        chb01_11.edf
        chb01_2.edf

    Natural sorting produces the expected numerical order:

        chb01_1.edf
        chb01_2.edf
        chb01_10.edf
        chb01_11.edf

    This is useful because EDF files commonly use numbered filenames.

    Parameters
    ----------
    path : zipfile.ZipInfo
        File entry inside the uploaded ZIP archive.

    Returns
    -------
    list
        Sorting key containing numeric and textual filename components.
    """

    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.filename)
    ]


def _edf_members(
    archive: zipfile.ZipFile,
) -> list[zipfile.ZipInfo]:
    """
    Find all EDF files contained in a ZIP archive.

    The ZIP does not have to contain EDF files directly at its root.

    For example, this is valid:

        chb01/
            chb01_01.edf
            chb01_02.edf
            chb01_03.edf

    Only regular files with the ``.edf`` extension are returned.

    The resulting list is naturally sorted so that EDF sequence numbers
    appear in the expected order.

    Parameters
    ----------
    archive : zipfile.ZipFile
        Open ZIP archive uploaded by the client.

    Returns
    -------
    list[zipfile.ZipInfo]
        EDF files found in the archive.

    Raises
    ------
    ValueError
        If no EDF files are found.

    ValueError
        If the archive contains more than MAX_EDF_FILES_PER_ARCHIVE EDF files.
    """

    members = [
        member
        for member in archive.infolist()
        if (
            not member.is_dir()
            and Path(member.filename).suffix.lower() == ".edf"
        )
    ]

    if not members:
        raise ValueError(
            "ZIP archive does not contain any EDF files."
        )

    if len(members) > MAX_EDF_FILES_PER_ARCHIVE:
        raise ValueError(
            f"ZIP archive contains more than "
            f"{MAX_EDF_FILES_PER_ARCHIVE} EDF files."
        )

    return sorted(
        members,
        key=_natural_sort_key,
    )


# ============================================================================
# DE-IDENTIFICATION ENDPOINT
# ============================================================================

@router.post(
    "/deidentify",
    status_code=201,
    deprecated=True,
)
async def deidentify_eeg_archive(
    archive: UploadFile = File(...),
    patient_reference: str = Form(...),
    db: Session = Depends(get_session),
):
    """
    Upload and de-identify a complete EEG session.

    The client uploads:

        1. A ZIP archive containing one or more EDF files.
        2. A patient reference supplied by the clinical/frontend system.

    Example:

        patient_reference = "HUKM-12345"

        archive:
            chb01/
                chb01_01.edf
                chb01_02.edf
                chb01_03.edf

    The patient reference is stored ONLY in the controlled database layer.

    Each EDF receives its own generated recording ID:

        REC-A81F2391
        REC-B72C9120
        REC-13FD812A

    The de-identified EDF contains the generated recording ID instead of
    the original patient-identifying fields.

    The resulting architecture is:

        patient_reference
               │
               ▼
          EEGSession
               │
               ├── REC-001
               │      └── REC-001.edf
               │
               ├── REC-002
               │      └── REC-002.edf
               │
               └── REC-003
                      └── REC-003.edf

    The model receives the REC-* identifier, not the patient reference.

    Parameters
    ----------
    archive : UploadFile
        ZIP archive containing EDF recordings.

    patient_reference : str
        Restricted clinical reference used by the backend to associate
        results with the correct patient.

    db : Session
        SQLModel database session supplied by FastAPI.

    Returns
    -------
    dict
        Session ID, processing summary, and public recording information.

    Raises
    ------
    HTTPException
        400 if the uploaded file is not a ZIP archive.

    HTTPException
        400 if patient_reference is missing.

    HTTPException
        400 if the ZIP archive is invalid or cannot be processed.
    """

    # ------------------------------------------------------------------------
    # 1. Validate the uploaded archive
    # ------------------------------------------------------------------------

    if (
        not archive.filename
        or not archive.filename.lower().endswith(".zip")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Upload one ZIP archive containing EDF files."
            ),
        )

    # A patient reference is required because the backend needs a controlled
    # way to associate the resulting EEG analysis with the correct patient.
    if not patient_reference.strip():
        raise HTTPException(
            status_code=400,
            detail="patient_reference is required.",
        )

    # ------------------------------------------------------------------------
    # 2. Open and validate the ZIP archive
    # ------------------------------------------------------------------------

    try:
        zip_file = zipfile.ZipFile(archive.file)

    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid ZIP archive.",
        ) from exc

    try:
        members = _edf_members(zip_file)

    except ValueError as exc:
        zip_file.close()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ------------------------------------------------------------------------
    # 3. Create an EEG session in the database
    # ------------------------------------------------------------------------

    # One uploaded ZIP represents one EEG session.
    #
    # The patient reference is stored here and is NOT written into the
    # de-identified EDF that will later be given to the model.
    eeg_session = EEGSession(
        session_id=_new_session_id(),
        patient_reference=patient_reference.strip(),
    )

    db.add(eeg_session)
    db.commit()
    db.refresh(eeg_session)

    # Ensure the directories used for temporary and de-identified files exist.
    ensure_storage_directories()

    records: list[EEGRecording] = []

    # ------------------------------------------------------------------------
    # 4. Process every EDF in the ZIP archive
    # ------------------------------------------------------------------------

    try:

        for sequence_index, member in enumerate(
            members,
            start=1,
        ):

            # --------------------------------------------------------------
            # 4a. Create database record
            # --------------------------------------------------------------

            # Every EDF gets its own REC-* identifier.
            #
            # The original filename is stored for internal traceability,
            # while the generated REC-* ID becomes the identifier used by
            # the rest of the privacy-preserving pipeline.
            record = EEGRecording(
                record_id=generate_record_id(),
                session_db_id=eeg_session.id,
                sequence_index=sequence_index,
                original_filename=Path(member.filename).name,
            )

            db.add(record)
            db.commit()
            db.refresh(record)

            # Temporary path for the uploaded EDF.
            #
            # This file is removed after de-identification.
            input_path = (
                INCOMING_DIR
                / f"{uuid.uuid4().hex}.edf"
            )

            # Permanent path for the de-identified EDF.
            #
            # The filename does NOT contain the original patient filename.
            output_path = (
                DEIDENTIFIED_DIR
                / f"{record.record_id}.edf"
            )

            try:

                # ----------------------------------------------------------
                # 4b. Copy the EDF from the ZIP to temporary storage
                # ----------------------------------------------------------

                with (
                    zip_file.open(member) as source,
                    input_path.open("wb") as destination,
                ):
                    shutil.copyfileobj(
                        source,
                        destination,
                    )

                # ----------------------------------------------------------
                # 4c. Inspect EDF metadata
                # ----------------------------------------------------------

                # This checks the EDF header for technical information and
                # determines whether potentially identifying fields exist.
                #
                # Raw patient-identifying values should NOT be returned
                # through the API.
                metadata = inspect_metadata(input_path)

                # ----------------------------------------------------------
                # 4d. Create the de-identified EDF
                # ----------------------------------------------------------

                # The original EDF is NOT modified.
                #
                # Instead, a new EDF is written using REC-* as its internal
                # recording identifier.
                deidentify_edf(
                    input_path,
                    output_path,
                    record.record_id,
                )

                # ----------------------------------------------------------
                # 4e. Store technical metadata in the database
                # ----------------------------------------------------------

                technical = metadata["technical"]

                record.deidentified_path = str(
                    output_path.relative_to(PROJECT_ROOT)
                )

                record.duration_seconds = (
                    technical["duration_seconds"]
                )

                # Currently we take the first channel's sampling frequency.
                #
                # This assumes the recording uses the same sampling rate
                # across all channels, which is true for the CHB-MIT data.
                record.sampling_rate = int(
                    technical["sampling_frequencies_hz"][0]
                )

                record.channel_count = (
                    technical["number_of_channels"]
                )

                record.status = RecordingStatus.DEIDENTIFIED

            except Exception as exc:

                # If one EDF fails, mark only that recording as failed.
                # Other EDF files in the same session can still be processed.
                record.status = RecordingStatus.FAILED
                record.error_message = str(exc)

            finally:

                # The original uploaded EDF is temporary.
                #
                # After de-identification, the backend keeps only the
                # de-identified copy.
                input_path.unlink(
                    missing_ok=True
                )

            # Persist the final status and metadata.
            db.add(record)
            db.commit()
            db.refresh(record)

            records.append(record)

    finally:

        # Always close the ZIP file even if processing raises an exception.
        zip_file.close()

    # ------------------------------------------------------------------------
    # 5. Build the response
    # ------------------------------------------------------------------------

    completed = sum(
        record.status == RecordingStatus.DEIDENTIFIED
        for record in records
    )

    return {
        "session_id": eeg_session.session_id,

        "summary": {
            "edf_files_found": len(members),
            "deidentified": completed,
            "failed": len(records) - completed,
        },

        "records": [
            _public_record(
                record,
                eeg_session.session_id,
            )
            for record in records
        ],
    }


# ============================================================================
# PREPROCESSING ENDPOINT
# ============================================================================

@router.post(
    "/preprocess/{session_id}",
    deprecated=True,
)
def preprocess_eeg_session(
    session_id: str,
    db: Session = Depends(get_session),
):
    """
    Preprocess all de-identified EDF files belonging to an EEG session.

    The frontend does NOT upload the EDF again.

    Instead, the client provides the session ID:

        POST /api/v1/preprocess/SES-7A31F2C9

    The backend then:

        1. Finds the EEGSession.
        2. Finds all EEGRecording records belonging to that session.
        3. Retrieves each de-identified EDF path.
        4. Runs the preprocessing pipeline.
        5. Saves the model-ready NPZ artifact.
        6. Updates the database status.
        7. Returns information about the generated model input.

    Pipeline:

        EEGSession
             │
             ├── REC-001
             │      │
             │      └── deidentified EDF
             │               │
             │               ▼
             │          preprocessing
             │               │
             │               ▼
             │          model-ready NPZ
             │
             ├── REC-002
             │      └── ...
             │
             └── REC-003
                    └── ...

    Parameters
    ----------
    session_id : str
        Public session identifier.

    db : Session
        SQLModel database session.

    Returns
    -------
    dict
        Processing status and model-input information for each EDF.

    Raises
    ------
    HTTPException
        404 if the session does not exist.

    HTTPException
        409 if the session contains no recordings.
    """

    # ------------------------------------------------------------------------
    # 1. Find the EEG session
    # ------------------------------------------------------------------------

    eeg_session = db.exec(
        select(EEGSession).where(
            EEGSession.session_id == session_id
        )
    ).first()

    if eeg_session is None:
        raise HTTPException(
            status_code=404,
            detail="EEG session was not found.",
        )

    # ------------------------------------------------------------------------
    # 2. Retrieve all EDF recordings belonging to the session
    # ------------------------------------------------------------------------

    records = db.exec(
        select(EEGRecording)
        .where(
            EEGRecording.session_db_id == eeg_session.id
        )
        .order_by(
            EEGRecording.sequence_index
        )
    ).all()

    if not records:
        raise HTTPException(
            status_code=409,
            detail="This session has no EDF recordings.",
        )

    results = []

    # ------------------------------------------------------------------------
    # 3. Process each EDF recording
    # ------------------------------------------------------------------------

    for record in records:

        # Only de-identified files should enter the preprocessing pipeline.
        #
        # This is an important privacy boundary:
        #
        #     original EDF
        #          ↓
        #     de-identification
        #          ↓
        #     de-identified EDF
        #          ↓
        #     preprocessing
        #          ↓
        #     model
        #
        if record.status not in {
            RecordingStatus.DEIDENTIFIED,
            RecordingStatus.PROCESSED,
        }:

            results.append({
                "record": _public_record(
                    record,
                    session_id,
                ),
                "model_input": None,
            })

            continue

        # A database record marked as de-identified must have a corresponding
        # de-identified EDF path.
        if not record.deidentified_path:

            record.status = RecordingStatus.FAILED

            record.error_message = (
                "No deidentified EDF is linked to this record."
            )

            db.add(record)
            db.commit()

            results.append({
                "record": _public_record(
                    record,
                    session_id,
                ),
                "model_input": None,
            })

            continue

        # Convert the relative database path back into a path on the server.
        input_path = (
            PROJECT_ROOT
            / record.deidentified_path
        )

        try:

            # --------------------------------------------------------------
            # 3a. Mark recording as currently processing
            # --------------------------------------------------------------

            record.status = RecordingStatus.PROCESSING
            record.error_message = None

            db.add(record)
            db.commit()

            # --------------------------------------------------------------
            # 3b. Run EEG preprocessing
            # --------------------------------------------------------------

            # The preprocessing service is responsible for things such as:
            #
            #     - reading the EDF
            #     - filtering
            #     - normalization
            #     - artifact handling
            #     - windowing
            #     - creating model-ready arrays
            #
            # This endpoint only coordinates the process.
            output_path, details = preprocess_edf_to_npz(
                input_path,
                record.record_id,
            )

            # --------------------------------------------------------------
            # 3c. Store the generated model artifact
            # --------------------------------------------------------------

            record.preprocessed_path = str(
                output_path.relative_to(PROJECT_ROOT)
            )

            record.status = RecordingStatus.PROCESSED

            db.add(record)
            db.commit()
            db.refresh(record)

            # --------------------------------------------------------------
            # 3d. Return model-input information
            # --------------------------------------------------------------

            results.append({
                "record": _public_record(
                    record,
                    session_id,
                ),

                "model_input": {
                    "format": "npz",

                    "path": record.preprocessed_path,

                    "arrays": [
                        "model_windows",
                        "window_start_seconds",
                        "sampling_rate",
                        "channel_labels",
                    ],

                    "shape": details[
                        "model_input_shape"
                    ],

                    "dtype": "float32",
                },

                **details,
            })

        except Exception as exc:

            # If preprocessing fails, retain the failure state in the DB.
            record.status = RecordingStatus.FAILED
            record.error_message = str(exc)

            db.add(record)
            db.commit()

            results.append({
                "record": _public_record(
                    record,
                    session_id,
                ),
                "model_input": None,
            })

    # ------------------------------------------------------------------------
    # 4. Return session-level processing summary
    # ------------------------------------------------------------------------

    processed = sum(
        item["record"]["status"]
        == RecordingStatus.PROCESSED
        for item in results
    )

    return {
        "session_id": session_id,

        "summary": {
            "processed": processed,
            "failed_or_skipped": (
                len(results) - processed
            ),
        },

        "records": results,
    }
