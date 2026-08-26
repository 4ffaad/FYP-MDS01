"""EDF de-identification utilities.

The source EDF is never modified in place. A new EDF is written with the same
digital samples, required channel labels, and sampling frequencies, while
identifying and free-text header fields are cleared. The generated recording
identifier stays in the database and is never written into the EDF.
"""

from datetime import datetime
import math
from pathlib import Path
import secrets

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
    return f"REC-{secrets.token_hex(16).upper()}"


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


def _safe_physical_bounds(header: dict) -> tuple[float, float]:
    """Return EDF-serializable bounds that still contain source bounds."""

    try:
        source_min = float(header["physical_min"])
        source_max = float(header["physical_max"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("EDF signal header has invalid physical bounds.") from exc
    if not math.isfinite(source_min) or not math.isfinite(source_max) or source_min >= source_max:
        raise ValueError("EDF signal header has invalid physical bounds.")

    # EDF stores these fields in eight-character slots. Round outward so the
    # digital samples remain valid under a nearby linear calibration.
    for decimals in range(6, -1, -1):
        scale = 10**decimals
        physical_min = float(f"{math.floor(source_min * scale) / scale:.{decimals}f}")
        physical_max = float(f"{math.ceil(source_max * scale) / scale:.{decimals}f}")
        if (
            physical_min < physical_max
            and physical_min <= source_min
            and physical_max >= source_max
            and len(str(physical_min)) <= 8
            and len(str(physical_max)) <= 8
        ):
            return physical_min, physical_max
    raise ValueError("EDF physical bounds cannot be represented safely.")


def scrub_signal_header(
    header: dict,
    label: str | None = None,
    digital_samples=None,
) -> dict:
    """Return one signal header with scrubbed text and safe calibration ranges.

    When samples extend beyond the source digital range, the range is widened
    before writing. The source linear calibration is retained, so the digital
    samples are not clipped by the EDF writer.
    """

    scrubbed = dict(header)
    if label is not None:
        scrubbed["label"] = label
    scrubbed["transducer"] = ""
    scrubbed["prefilter"] = ""

    try:
        digital_min = int(header["digital_min"])
        digital_max = int(header["digital_max"])
        physical_min = float(header["physical_min"])
        physical_max = float(header["physical_max"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("EDF signal header has invalid calibration fields.") from exc
    if digital_min >= digital_max or physical_min >= physical_max:
        raise ValueError("EDF signal header has invalid calibration fields.")

    if digital_samples is not None:
        if len(digital_samples):
            actual_min = int(digital_samples.min())
            actual_max = int(digital_samples.max())
            expanded_min = min(digital_min, actual_min)
            expanded_max = max(digital_max, actual_max)
            if (expanded_min, expanded_max) != (digital_min, digital_max):
                slope = (physical_max - physical_min) / (digital_max - digital_min)
                intercept = physical_min - digital_min * slope
                digital_min, digital_max = expanded_min, expanded_max
                physical_min = intercept + digital_min * slope
                physical_max = intercept + digital_max * slope

    if len(str(digital_min)) > 8 or len(str(digital_max)) > 8:
        raise ValueError("EDF digital bounds cannot be represented safely.")
    scrubbed["digital_min"] = digital_min
    scrubbed["digital_max"] = digital_max
    scrubbed["physical_min"], scrubbed["physical_max"] = _safe_physical_bounds(
        {"physical_min": physical_min, "physical_max": physical_max}
    )
    return scrubbed


def _verify_scrubbed_edf(edf_path: Path) -> None:
    """Reopen a scrubbed EDF and reject identifiers or free-text leakage."""

    reader = pyedflib.EdfReader(str(edf_path))
    try:
        signal_headers = reader.getSignalHeaders()
        if any(
            _contains_identifier(str(header.get("transducer") or ""))
            or _contains_identifier(str(header.get("prefilter") or ""))
            for header in signal_headers
        ):
            raise ValueError("Scrubbed EDF contains signal-header text.")
        _onsets, _durations, descriptions = reader.readAnnotations()
        if any(str(description).strip() for description in descriptions):
            raise ValueError("Scrubbed EDF contains annotation descriptions.")
    finally:
        reader.close()
    metadata = inspect_metadata(edf_path)
    if any(metadata["potential_identifiers_present"].values()):
        raise ValueError("Scrubbed EDF contains identifying metadata.")


def deidentify_edf(input_path: str | Path, output_path: str | Path, record_id: str) -> Path:
    """
    Write a metadata-scrubbed copy of an EDF while preserving EEG data exactly.

    Digital samples are copied rather than calibrated physical values.  This
    avoids a second analogue-to-digital conversion and preserves the source
    signal values, labels and sample frequencies. Privacy-sensitive transducer
    and prefilter text is cleared rather than copied.
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
        digital_signals = [
            reader.readSignal(channel, digital=True)
            for channel in range(reader.signals_in_file)
        ]
        signal_headers = [
            scrub_signal_header(
                header,
                str(header.get("label", "")).strip(),
                digital_signals[index],
            )
            for index, header in enumerate(reader.getSignalHeaders())
        ]
        # Physical ranges were normalized by scrub_signal_header so pyedflib
        # can encode them in EDF+'s fixed-width fields without truncation.
        # Digital samples remain unchanged; only the serialized calibration
        # metadata is made safe for the scrubbed processing artifact.
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

    try:
        _verify_scrubbed_edf(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination
