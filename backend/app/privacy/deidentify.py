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

import numpy as np
import pyedflib

from backend.app.eeg.contracts import MODEL_CHANNELS

_NEUTRAL_START_DATETIME = datetime(1970, 1, 1)


def _contains_identifier(value: str) -> bool:
    """Return whether an EDF text field contains meaningful metadata.

    ``pyedflib`` represents an empty EDF patient-name field as ``X``. That
    format placeholder is not identifying metadata and must not make a
    scrubbed file appear unsanitized.
    """

    normalized = value.strip().upper()
    return bool(normalized) and normalized not in {"X", "X X X X"}


def _reviewed_channel_indexes(labels: list[str]) -> list[int]:
    """Return the exact reviewed model montage order, rejecting ambiguity."""

    matches: dict[str, int] = {}
    for index, raw_label in enumerate(labels):
        label = str(raw_label).strip()
        if label not in MODEL_CHANNELS:
            continue
        if label in matches:
            raise ValueError("EEG contains an ambiguous reviewed model channel.")
        matches[label] = index
    if any(label not in matches for label in MODEL_CHANNELS):
        raise ValueError("EEG does not contain the reviewed 18-channel montage.")
    return [matches[label] for label in MODEL_CHANNELS]


def generate_record_id() -> str:
    """Return a random identifier for one EEG recording, unrelated to PII."""
    return f"REC-{secrets.token_hex(16).upper()}"


def inspect_metadata(edf_path: str | Path) -> dict:
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
        signal_labels = [str(label).strip() for label in reader.getSignalLabels()]
        potential_identifiers_present = {
            "patient_code": _contains_identifier(patient_code),
            "patient_name": _contains_identifier(patient_name),
            "patient_additional": _contains_identifier(reader.getPatientAdditional()),
            "birthdate": _contains_identifier(reader.getBirthdate()),
            "technician": _contains_identifier(reader.getTechnician()),
            "equipment": _contains_identifier(reader.getEquipment()),
            "admincode": _contains_identifier(reader.getAdmincode()),
            "recording_additional": _contains_identifier(reader.getRecordingAdditional()),
            "sex": _contains_identifier(reader.getSex()),
            "recording_datetime": reader.getStartdatetime() != _NEUTRAL_START_DATETIME,
            "non_model_channel_labels": any(label not in MODEL_CHANNELS for label in signal_labels),
        }
        return {
            "technical": {
                "number_of_channels": reader.signals_in_file,
                "channel_labels": [
                    label if label in MODEL_CHANNELS else "<redacted>"
                    for label in signal_labels
                ],
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
    # EDF's physical-dimension field is not part of the model contract and
    # may contain free text; preserve sample/calibration values without it.
    scrubbed["dimension"] = ""
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
        if reader.getSignalLabels() != list(MODEL_CHANNELS):
            raise ValueError("Scrubbed EDF does not contain the reviewed model channels.")
        if reader.getStartdatetime() != _NEUTRAL_START_DATETIME:
            raise ValueError("Scrubbed EDF contains a non-neutral recording date.")
        if _contains_identifier(reader.getSex()):
            raise ValueError("Scrubbed EDF contains demographic metadata.")
        signal_headers = reader.getSignalHeaders()
        if any(
            str(header.get("dimension") or "") not in {"", "V"}
            or _contains_identifier(str(header.get("transducer") or ""))
            or _contains_identifier(str(header.get("prefilter") or ""))
            for header in signal_headers
        ):
            raise ValueError("Scrubbed EDF contains unsafe signal-header metadata.")
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
    Write a metadata-scrubbed EDF with only the reviewed model montage.

    Digital samples for the exact reviewed 18-channel montage are copied rather
    than recalibrated. Other channels are dropped so arbitrary channel labels
    cannot carry patient metadata into the model-input artifact. Missing or
    duplicate reviewed channels fail closed.
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
        source_labels = [str(label).strip() for label in reader.getSignalLabels()]
        channel_indexes = _reviewed_channel_indexes(source_labels)
        source_headers = reader.getSignalHeaders()
        digital_signals = [
            reader.readSignal(channel_index, digital=True)
            for channel_index in channel_indexes
        ]
        signal_headers = [
            scrub_signal_header(
                source_headers[channel_index],
                model_label,
                digital_signals[index],
            )
            for index, (model_label, channel_index) in enumerate(
                zip(MODEL_CHANNELS, channel_indexes, strict=True)
            )
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
            len(MODEL_CHANNELS),
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


def deidentify_nicolet(input_path: str | Path, output_path: str | Path, record_id: str) -> Path:
    """Convert Nicolet samples to an identifier-free scrubbed EDF.

    The Nicolet ``.head`` file is never copied. Signal data is read through
    MNE, written to a new EDF with neutral metadata, and verified using the
    same scrubbed-EDF checks as native EDF input. Annotation descriptions are
    deliberately blanked while relative timing is retained.
    """

    del record_id
    from backend.app.eeg.io import read_nicolet_bounded

    source = Path(input_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = None
    writer = None
    try:
        raw = read_nicolet_bounded(source)
        source_labels = [str(label).strip() for label in raw.ch_names]
        signals = np.asarray(raw.get_data(), dtype=np.float64)
        if signals.ndim != 2 or signals.shape[0] != len(source_labels):
            raise ValueError("Nicolet signal data cannot be safely de-identified.")
        channel_indexes = _reviewed_channel_indexes(source_labels)
        signals = signals[channel_indexes]
        labels = list(MODEL_CHANNELS)
        sampling_rate = float(raw.info["sfreq"])
        if (
            signals.ndim != 2
            or signals.shape[0] != len(labels)
            or not labels
            or len(labels) != len(set(labels))
            or any(not label for label in labels)
            or not np.isfinite(signals).all()
            or sampling_rate <= 0
            or sampling_rate != round(sampling_rate)
        ):
            raise ValueError("Nicolet signal data cannot be safely de-identified.")

        signal_headers = []
        for channel_index, label in enumerate(labels):
            if len(label) > 16:
                raise ValueError("Nicolet channel label exceeds the EDF label limit.")
            channel = signals[channel_index]
            peak = float(np.max(np.abs(channel)))
            if not np.isfinite(peak):
                raise ValueError("Nicolet signal contains non-finite values.")
            peak = max(peak * 1.05, 1e-6)
            physical_min, physical_max = _safe_physical_bounds(
                {"physical_min": -peak, "physical_max": peak}
            )
            signal_headers.append(
                {
                    "label": label,
                    "dimension": "V",
                    "sample_frequency": int(round(sampling_rate)),
                    "physical_min": physical_min,
                    "physical_max": physical_max,
                    "digital_min": -32768,
                    "digital_max": 32767,
                    "transducer": "",
                    "prefilter": "",
                }
            )

        writer = pyedflib.EdfWriter(
            str(destination),
            len(labels),
            file_type=pyedflib.FILETYPE_EDFPLUS,
        )
        writer.setHeader(
            {
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
        )  # type: ignore[arg-type]
        writer.setSignalHeaders(signal_headers)
        writer.writeSamples([channel for channel in signals], digital=False)
        for onset, duration in zip(raw.annotations.onset.tolist(), raw.annotations.duration.tolist()):
            writer.writeAnnotation(float(onset), float(duration), "")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if writer is not None:
            writer.close()
        if raw is not None:
            raw.close()

    try:
        _verify_scrubbed_edf(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def deidentify_legacy_nicolet(input_path: str | Path, output_path: str | Path, record_id: str) -> Path:
    """Convert a legacy single-file Nicolet recording to a scrubbed EDF."""

    del record_id
    from backend.app.eeg.io import read_uniform_legacy_eeg_segments

    segments, sampling_rate, source_labels = read_uniform_legacy_eeg_segments(input_path)
    if not segments or any(
        signals.ndim != 2 or signals.shape[0] != len(source_labels)
        for _start_seconds, signals in segments
    ):
        raise ValueError("Legacy Nicolet signal data cannot be safely de-identified.")
    channel_indexes = _reviewed_channel_indexes(source_labels)
    total_samples = sum(signals.shape[1] for _start_seconds, signals in segments)
    signals = np.empty((len(channel_indexes), total_samples), dtype=np.float32)
    sample_start = 0
    for _start_seconds, segment_signals in segments:
        sample_end = sample_start + segment_signals.shape[1]
        signals[:, sample_start:sample_end] = segment_signals[channel_indexes]
        sample_start = sample_end
    del segments
    labels = list(MODEL_CHANNELS)
    if (
        signals.ndim != 2
        or signals.shape[0] != len(labels)
        or not labels
        or len(labels) != len(set(labels))
        or not np.isfinite(signals).all()
        or sampling_rate <= 0
    ):
        raise ValueError("Legacy Nicolet signal data cannot be safely de-identified.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    try:
        signal_headers = []
        for channel_index, label in enumerate(labels):
            if len(label) > 16:
                raise ValueError("Legacy Nicolet channel label exceeds the EDF label limit.")
            channel = signals[channel_index]
            peak = float(np.max(np.abs(channel)))
            if not np.isfinite(peak):
                raise ValueError("Legacy Nicolet signal contains non-finite values.")
            peak = max(peak * 1.05, 1e-6)
            physical_min, physical_max = _safe_physical_bounds(
                {"physical_min": -peak, "physical_max": peak}
            )
            signal_headers.append(
                {
                    "label": label,
                    "dimension": "V",
                    "sample_frequency": int(sampling_rate),
                    "physical_min": physical_min,
                    "physical_max": physical_max,
                    "digital_min": -32768,
                    "digital_max": 32767,
                    "transducer": "",
                    "prefilter": "",
                }
            )
        writer = pyedflib.EdfWriter(
            str(destination), len(labels), file_type=pyedflib.FILETYPE_EDFPLUS
        )
        writer.setHeader(
            {
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
        )
        writer.setSignalHeaders(signal_headers)
        writer.writeSamples([channel for channel in signals], digital=False)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if writer is not None:
            writer.close()

    try:
        _verify_scrubbed_edf(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def deidentify_eeg(input_path: str | Path, output_path: str | Path, record_id: str) -> Path:
    """De-identify either native EDF or Nicolet input."""

    suffix = Path(input_path).suffix.lower()
    if suffix == ".edf":
        return deidentify_edf(input_path, output_path, record_id)
    if suffix == ".data":
        return deidentify_nicolet(input_path, output_path, record_id)
    if suffix == ".e":
        return deidentify_legacy_nicolet(input_path, output_path, record_id)
    raise ValueError("Unsupported EEG format for de-identification.")
