"""EDF de-identification utilities.

The source EDF is never modified in place.  A new EDF is written with the
same digital samples and signal headers, while patient-identifying header
fields are cleared or replaced by a newly generated recording identifier.
"""

from pathlib import Path
import uuid

import pyedflib


def generate_record_id() -> str:
    """Return a random identifier for one EEG recording, unrelated to PII."""
    return f"REC-{uuid.uuid4().hex[:8].upper()}"


def generate_anonymous_id() -> str:
    """Backward-compatible alias for :func:`generate_record_id`."""
    return generate_record_id()


def inspect_metadata(edf_path: str) -> dict:
    """
    Return safe technical metadata and flags showing whether PII is present.

    Raw values such as a patient name are deliberately not returned to an API
    caller.  They are only read here to determine whether de-identification is
    required.
    """
    reader = pyedflib.EdfReader(str(edf_path))

    try:
        patient_name = reader.getPatientName().strip()
        patient_code = reader.getPatientCode().strip()
        is_deidentified = (
            (patient_name.startswith("ANON-") or patient_name.startswith("REC-"))
            and patient_name == patient_code
        )
        return {
            "technical": {
                "number_of_channels": reader.signals_in_file,
                "channel_labels": reader.getSignalLabels(),
                "sampling_frequencies_hz": reader.getSampleFrequencies().tolist(),
                "duration_seconds": reader.getFileDuration(),
                "equipment": reader.getEquipment(),
            },
            "potential_identifiers_present": {
                # Our generated ANON-* value is a record reference, not PII.
                "patient_code": bool(patient_code) and not is_deidentified,
                "patient_name": bool(patient_name) and not is_deidentified,
                "patient_additional": bool(reader.getPatientAdditional().strip()),
                "birthdate": bool(reader.getBirthdate().strip()),
                "technician": bool(reader.getTechnician().strip()),
                "admincode": bool(reader.getAdmincode().strip()),
                "recording_additional": bool(reader.getRecordingAdditional().strip()),
            },
            "is_deidentified": is_deidentified,
        }
    finally:
        reader.close()


def deidentify_edf(input_path: str | Path, output_path: str | Path, anonymous_id: str) -> Path:
    """
    Write a de-identified copy of an EDF while preserving EEG data exactly.

    Digital samples are copied rather than calibrated physical values.  This
    avoids a second analogue-to-digital conversion and preserves the source
    signal values, labels, sample frequencies, units and filters.
    Start time and EDF annotations are preserved for temporal alignment.
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

        # Equipment can be useful for technical interpretation.  Personal and
        # administrative fields are blanked; the random ID labels this record.
        safe_header = {
            "technician": "",
            "recording_additional": "",
            "patientname": anonymous_id,
            "patient_additional": "",
            "patientcode": anonymous_id,
            "equipment": reader.getEquipment(),
            "admincode": "",
            "sex": "",
            "startdate": reader.getStartdatetime(),
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

        # EDF+ annotations carry onset/duration information needed for seizure
        # alignment, so retain them instead of stripping timestamps blindly.
        for onset, duration, description in zip(*annotations):
            writer.writeAnnotation(float(onset), float(duration), str(description))
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        if writer is not None:
            writer.close()
        reader.close()

    return destination
