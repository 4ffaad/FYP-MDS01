"""EDF de-identification utilities.

The source EDF is never modified in place.  A new EDF is written with the
    same digital samples and technical signal headers, while patient-identifying
    header fields are cleared. The generated recording identifier stays in the
    database and is never written into the EDF.
"""

from datetime import datetime
from pathlib import Path
import uuid

import pyedflib


def _contains_identifier(value: str) -> bool:
    """Return whether an EDF text field contains meaningful metadata.

    ``pyedflib`` represents an empty EDF patient-name field as ``X``. That
    format placeholder is not identifying metadata and must not make a
    scrubbed file appear unsanitized.
    """

    normalized = value.strip().upper()
    return bool(normalized) and normalized not in {"X", "X X X X"}


def generate_record_id() -> str:
    """Return a random identifier for one EEG recording, unrelated to PII."""
    return f"REC-{uuid.uuid4().hex[:8].upper()}"


def inspect_metadata(edf_path: str) -> dict:
    """
    Return safe technical metadata and flags showing whether PII is present.

    Raw values such as a patient name are deliberately not returned to an API
    caller. They are only read here to determine whether de-identification is
    required.
    """
    reader = pyedflib.EdfReader(str(edf_path))

    try:
        patient_name = reader.getPatientName().strip()
        patient_code = reader.getPatientCode().strip()
        potential_identifiers_present = {
            "patient_code": _contains_identifier(patient_code),
            "patient_name": _contains_identifier(patient_name),
            "patient_additional": _contains_identifier(reader.getPatientAdditional()),
            "birthdate": _contains_identifier(reader.getBirthdate()),
            "technician": _contains_identifier(reader.getTechnician()),
            "equipment": _contains_identifier(reader.getEquipment()),
            "admincode": _contains_identifier(reader.getAdmincode()),
            "recording_additional": _contains_identifier(reader.getRecordingAdditional()),
        }
        return {
            "technical": {
                "number_of_channels": reader.signals_in_file,
                "channel_labels": reader.getSignalLabels(),
                "sampling_frequencies_hz": reader.getSampleFrequencies().tolist(),
                "duration_seconds": reader.getFileDuration(),
            },
            "potential_identifiers_present": potential_identifiers_present,
            "is_deidentified": not any(potential_identifiers_present.values()),
        }
    finally:
        reader.close()


def deidentify_edf(input_path: str | Path, output_path: str | Path, record_id: str) -> Path:
    """
    Write a metadata-scrubbed copy of an EDF while preserving EEG data exactly.

    Digital samples are copied rather than calibrated physical values.  This
    avoids a second analogue-to-digital conversion and preserves the source
    signal values, labels, sample frequencies, units and filters.
    Relative annotation timing is preserved, while the identifying calendar
    start date is normalized to a fixed neutral date.

    Parameters
    ----------
    input_path : str or pathlib.Path
        Source EDF path in private processing storage.
    output_path : str or pathlib.Path
        Destination for the scrubbed EDF.
    record_id : str
        Generated database identifier accepted by the pipeline; it is not
        written into the output EDF.
    """
    source = Path(input_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    reader = pyedflib.EdfReader(str(source))
    writer = None
    try:
        signal_headers = reader.getSignalHeaders()
        digital_signals = [
            reader.readSignal(channel, digital=True)
            for channel in range(reader.signals_in_file)
        ]
        # Some real-world EDFs (including individual CHB-MIT records) contain
        # samples outside their declared digital range.  EdfWriter correctly
        # clamps those values unless the range is expanded.  Expand only when
        # needed and adjust the physical range with the same calibration slope,
        # preserving both the original digital samples and physical amplitudes.
        for header, samples in zip(signal_headers, digital_signals):
            original_digital_min = header["digital_min"]
            original_digital_max = header["digital_max"]
            actual_digital_min = min(original_digital_min, int(samples.min()))
            actual_digital_max = max(original_digital_max, int(samples.max()))
            if (actual_digital_min, actual_digital_max) != (
                original_digital_min,
                original_digital_max,
            ):
                slope = (
                    (header["physical_max"] - header["physical_min"])
                    / (original_digital_max - original_digital_min)
                )
                intercept = header["physical_min"] - original_digital_min * slope
                header["digital_min"] = actual_digital_min
                header["digital_max"] = actual_digital_max
                header["physical_min"] = intercept + actual_digital_min * slope
                header["physical_max"] = intercept + actual_digital_max * slope
        annotations = reader.readAnnotations()

        # Free-text EDF fields can carry patient, operator, or device details.
        # The record ID remains in PostgreSQL only; it is not written into EDF.
        safe_header = {
            "technician": "",
            "recording_additional": "",
            "patientname": "",
            "patient_additional": "",
            "patientcode": "",
            "equipment": "",
            "admincode": "",
            "sex": "",
            "startdate": datetime(1970, 1, 1),
            "birthdate": "",
        }

        writer = pyedflib.EdfWriter(
            str(destination),
            reader.signals_in_file,
            file_type=reader.filetype,
        )
        writer.setHeader(safe_header)
        writer.setSignalHeaders(signal_headers)
        writer.writeSamples(digital_signals, digital=True)

        # Preserve relative timing for seizure alignment, but remove all
        # free-text descriptions because they can contain clinical identifiers.
        for onset, duration, description in zip(*annotations):
            writer.writeAnnotation(float(onset), float(duration), "")
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        if writer is not None:
            writer.close()
        reader.close()

    return destination
