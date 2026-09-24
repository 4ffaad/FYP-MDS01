"""Bounded reader for legacy single-file Nicolet/Nervus ``.e`` EEG files.

The layout is based on the public FieldTrip and ieeg-portal Nicolet readers,
but this module intentionally exposes only technical signal metadata and
sanitized event classes. Patient-information packets and free-text event labels
are never decoded or returned.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import os
from pathlib import Path
import stat
import struct
from typing import BinaryIO, cast

import numpy as np
from scipy.signal import resample_poly

from backend.app.eeg.contracts import MODEL_CHANNELS, MODEL_SAMPLING_RATE

_MAX_FILE_BYTES = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_BYTES", str(2 * 1024**3)))
_MAX_INDEX_ENTRIES = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_INDEX_ENTRIES", "1000000"))
_MAX_STATIC_PACKETS = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_STATIC_PACKETS", "8192"))
_MAX_SEGMENTS = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_SEGMENTS", "10000"))
_MAX_EVENTS = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_EVENTS", "100000"))
_MAX_METADATA_PACKET_BYTES = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_METADATA_BYTES", str(64 * 1024**2)))
_MAX_EVENT_PACKET_BYTES = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_EVENT_BYTES", str(16 * 1024**2)))
_MAX_EVENT_SECTION_BYTES = 64 * 1024**2
_MAX_EVENT_SEGMENT_COMPARISONS = 1_000_000
_EVENT_SCAN_CHUNK_BYTES = 64 * 1024
_MAX_SIGNAL_SAMPLES = int(os.getenv("MDS01_MAX_LEGACY_NICOLET_SAMPLES", "5000000"))

if any(
    value <= 0
    for value in (
        _MAX_FILE_BYTES,
        _MAX_INDEX_ENTRIES,
        _MAX_STATIC_PACKETS,
        _MAX_SEGMENTS,
        _MAX_EVENTS,
        _MAX_METADATA_PACKET_BYTES,
        _MAX_EVENT_PACKET_BYTES,
        _MAX_EVENT_SECTION_BYTES,
        _MAX_EVENT_SEGMENT_COMPARISONS,
        _MAX_SIGNAL_SAMPLES,
    )
):
    raise RuntimeError("Legacy Nicolet limits must be positive.")

_DAY_SECONDS = 86400.0
_NICOLET_EPOCH_OFFSET = 2209161600.0
_EVENT_PACKET_GUID = bytes.fromhex("80F699B7A472D31193D300500400C148")
_STATIC_TAG_ALIASES = {
    "{A271CCCB-515D-4590-B6A1-DC170C8D6EE2}": "TSGUID",
    "{E11C4CBA-0753-4655-A1E9-2B2309D1545B}": "VIDEOSYNCGUID",
    "{8032E68A-EA3E-42E8-893E-6E93C59ED515}": "SIGNALINFOGUID",
    "{D0B3FD0B-49D9-4BF0-8929-296DE5A55910}": "PATIENTINFOGUID",
}

_EVENT_ANNOTATION = "{A5A95612-A7F8-11CF-831A-0800091B5BDA}"
_EVENT_SEIZURE = "{A5A95646-A7F8-11CF-831A-0800091B5BDA}"
_EVENT_TYPES = {
    _EVENT_ANNOTATION: "manual_annotation",
    _EVENT_SEIZURE: "seizure_event",
    "{08784382-C765-11D3-90CE-00104B6F4F70}": "format_change",
    "{6FF394DA-D1B8-46DA-B78F-866C67CF02AF}": "photic",
    "{481DFC97-013C-4BC5-A203-871B0375A519}": "post_hyperventilation",
    "{725798BF-CD1C-4909-B793-6C7864C27AB7}": "review_progress",
    "{96315D79-5C24-4A65-B334-E31A95088D55}": "exam_start",
    "{A5A95608-A7F8-11CF-831A-0800091B5BDA}": "hyperventilation",
    "{A5A95617-A7F8-11CF-831A-0800091B5BDA}": "impedance",
    "{A71A6DB5-4150-48BF-B462-1C40521EBD6F}": "amplifier_disconnect",
    "{6387C7C8-6F98-4886-9AF4-FA750ED300DE}": "amplifier_reconnect",
    "{71EECE80-EBC4-41C7-BF26-E56911426FB4}": "recording_paused",
}
LEGACY_SOURCE_SAMPLING_RATE = 500
_LEGACY_MONTAGE_ALIASES = {"T3": "T7", "T4": "T8", "T5": "P7", "T6": "P8"}
_LEGACY_RESAMPLE_UP = MODEL_SAMPLING_RATE // math.gcd(LEGACY_SOURCE_SAMPLING_RATE, MODEL_SAMPLING_RATE)
_LEGACY_RESAMPLE_DOWN = LEGACY_SOURCE_SAMPLING_RATE // math.gcd(
    LEGACY_SOURCE_SAMPLING_RATE, MODEL_SAMPLING_RATE
)


class LegacyNicoletError(ValueError):
    """Raised when a legacy Nicolet file cannot be read safely."""


@dataclass(frozen=True)
class NicoletChannel:
    """One signal channel at the selected common sampling rate."""

    label: str
    sampling_rate: int
    scale: float
    section_id: int


@dataclass(frozen=True)
class NicoletSegment:
    """Technical timing for one contiguous recording segment."""

    start_seconds: float
    duration_seconds: float
    sample_count: int
    sample_start: int


def _validate_segment_continuity(
    segments: tuple[NicoletSegment, ...], sampling_rate: int
) -> None:
    """Reject segment gaps or overlaps before concatenated signal processing."""

    if sampling_rate <= 0:
        raise LegacyNicoletError("Legacy Nicolet segment sampling rate is invalid.")
    tolerance_seconds = max(1e-6, 0.5 / sampling_rate)
    for previous, current in zip(segments, segments[1:]):
        expected_start = previous.start_seconds + previous.duration_seconds
        if (
            not _finite(current.start_seconds)
            or abs(current.start_seconds - expected_start) > tolerance_seconds
        ):
            raise LegacyNicoletError("Legacy Nicolet recording segments are discontinuous.")


@dataclass(frozen=True)
class NicoletEvent:
    """Sanitized event timing and class without clinical free text."""

    onset_seconds: float
    duration_seconds: float
    kind: str
    text_present: bool


@dataclass(frozen=True)
class NicoletHeader:
    """Safe technical header returned by :class:`LegacyNicoletReader`."""

    sampling_rate: int
    channels: tuple[NicoletChannel, ...]
    segments: tuple[NicoletSegment, ...]
    total_samples: int
    events: tuple[NicoletEvent, ...]


def _canonical_electrode_label(label: str) -> str:
    """Normalize only known technical electrode spelling variants."""

    normalized = label.strip().upper().replace(" ", "")
    if normalized.startswith("EEG"):
        normalized = normalized[3:]
    if normalized.endswith("-REF"):
        normalized = normalized[:-4]
    return _LEGACY_MONTAGE_ALIASES.get(normalized, normalized)


def select_legacy_montage_channels(
    header: NicoletHeader,
) -> tuple[tuple[str, NicoletChannel, NicoletChannel], ...]:
    """Select source electrodes needed to derive the reviewed bipolar montage."""

    if header.sampling_rate != LEGACY_SOURCE_SAMPLING_RATE:
        raise LegacyNicoletError("Legacy Nicolet source sampling rate is unsupported.")
    required_electrodes = {
        electrode
        for model_label in MODEL_CHANNELS
        for electrode in model_label.split("-", 1)
    }
    source_by_electrode: dict[str, NicoletChannel] = {}
    for channel in header.channels:
        electrode = _canonical_electrode_label(channel.label)
        if electrode not in required_electrodes:
            continue
        if electrode in source_by_electrode:
            raise LegacyNicoletError("Legacy Nicolet source electrodes are ambiguous.")
        if channel.sampling_rate != LEGACY_SOURCE_SAMPLING_RATE:
            raise LegacyNicoletError("Legacy Nicolet source electrodes have mixed rates.")
        source_by_electrode[electrode] = channel
    try:
        return tuple(
            (
                model_label,
                source_by_electrode[model_label.split("-", 1)[0]],
                source_by_electrode[model_label.split("-", 1)[1]],
            )
            for model_label in MODEL_CHANNELS
        )
    except KeyError as exc:
        raise LegacyNicoletError("Legacy Nicolet source montage is missing a required electrode.") from exc


@dataclass(frozen=True)
class _IndexEntry:
    section_id: int
    offset: int
    section_length: int


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    if size < 0:
        raise LegacyNicoletError("Legacy Nicolet file is malformed.")
    data = stream.read(size)
    if len(data) != size:
        raise LegacyNicoletError("Legacy Nicolet file is truncated.")
    return data


def _decode_utf16_field(data: bytes) -> str:
    if len(data) % 2:
        raise LegacyNicoletError("Legacy Nicolet text field is malformed.")
    try:
        return data.decode("utf-16-le", errors="strict").split("\x00", 1)[0].strip()
    except UnicodeDecodeError as exc:
        raise LegacyNicoletError("Legacy Nicolet text field is malformed.") from exc


def _format_guid(data: bytes) -> str:
    if len(data) != 16:
        raise LegacyNicoletError("Legacy Nicolet event identifier is malformed.")
    return (
        f"{{{data[3]:02X}{data[2]:02X}{data[1]:02X}{data[0]:02X}-"
        f"{data[5]:02X}{data[4]:02X}-"
        f"{data[7]:02X}{data[6]:02X}-"
        f"{data[8]:02X}{data[9]:02X}-"
        f"{data[10]:02X}{data[11]:02X}{data[12]:02X}{data[13]:02X}{data[14]:02X}{data[15]:02X}}}"
    )


def _finite(value: float, *, positive: bool = False) -> bool:
    return math.isfinite(value) and (not positive or value > 0)


class LegacyNicoletReader:
    """Read one legacy Nicolet ``.e`` file with bounded allocations."""

    def __init__(self, path: str | Path) -> None:
        candidate = Path(path)
        if candidate.suffix.lower() != ".e":
            raise LegacyNicoletError("Legacy Nicolet input must use the .e extension.")
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise LegacyNicoletError("Legacy Nicolet file is unavailable.") from exc
        if candidate.is_symlink() or not candidate.is_file():
            raise LegacyNicoletError("Legacy Nicolet file is not a regular file.")
        if metadata.st_size <= 0 or metadata.st_size > _MAX_FILE_BYTES:
            raise LegacyNicoletError("Legacy Nicolet file exceeds the safe size limit.")
        self.path = candidate
        self._file_size = metadata.st_size
        self._header: NicoletHeader | None = None
        self._section_entries: dict[int, tuple[_IndexEntry, ...]] = {}
        self._first_segment_start_seconds = 0.0

    def _open_source(self) -> BinaryIO:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags)
        except OSError as exc:
            raise LegacyNicoletError("Legacy Nicolet file is unavailable.") from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != self._file_size:
                raise LegacyNicoletError("Legacy Nicolet file changed during validation.")
            return os.fdopen(descriptor, "rb", closefd=True)
        except Exception:
            os.close(descriptor)
            raise

    def _check_range(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0 or offset > self._file_size or size > self._file_size - offset:
            raise LegacyNicoletError("Legacy Nicolet file contains an invalid section range.")

    def _read_at(self, stream: BinaryIO, offset: int, size: int) -> bytes:
        self._check_range(offset, size)
        stream.seek(offset)
        return _read_exact(stream, size)

    def _read_indices(self, stream: BinaryIO, index_offset: int) -> dict[int, tuple[_IndexEntry, ...]]:
        if index_offset <= 0:
            raise LegacyNicoletError("Legacy Nicolet index is invalid.")
        raw_count = self._read_at(stream, 172208, 4)
        total_entries = struct.unpack("<I", raw_count)[0]
        if not 0 < total_entries <= _MAX_INDEX_ENTRIES:
            raise LegacyNicoletError("Legacy Nicolet index is invalid.")

        entries: dict[int, list[_IndexEntry]] = defaultdict(list)
        current_pointer = index_offset
        consumed = 0
        visited: set[int] = set()
        while consumed < total_entries:
            if current_pointer in visited:
                raise LegacyNicoletError("Legacy Nicolet index contains a cycle.")
            visited.add(current_pointer)
            self._check_range(current_pointer, 16)
            stream.seek(current_pointer)
            block_count = struct.unpack("<Q", _read_exact(stream, 8))[0]
            if not 0 < block_count <= total_entries - consumed:
                raise LegacyNicoletError("Legacy Nicolet index block is invalid.")
            values = np.frombuffer(_read_exact(stream, int(block_count) * 24), dtype="<u8")
            if values.size != block_count * 3:
                raise LegacyNicoletError("Legacy Nicolet index block is truncated.")
            values = values.reshape((int(block_count), 3))
            for section_id, offset, packed_length in values.tolist():
                section_length = int(packed_length >> 32)
                if section_length <= 0:
                    raise LegacyNicoletError("Legacy Nicolet section length is invalid.")
                self._check_range(int(offset), section_length)
                entries[int(section_id)].append(
                    _IndexEntry(int(section_id), int(offset), section_length)
                )
            consumed += int(block_count)
            current_pointer = struct.unpack("<Q", _read_exact(stream, 8))[0]
            if consumed < total_entries and current_pointer == 0:
                raise LegacyNicoletError("Legacy Nicolet index is incomplete.")
        return {section_id: tuple(values) for section_id, values in entries.items()}

    def _read_tags(self, stream: BinaryIO) -> dict[str, int]:
        stream.seek(172)
        count = struct.unpack("<I", _read_exact(stream, 4))[0]
        if not 0 < count <= _MAX_STATIC_PACKETS:
            raise LegacyNicoletError("Legacy Nicolet static packet table is invalid.")
        tags: dict[str, int] = {}
        for _ in range(count):
            tag = _decode_utf16_field(_read_exact(stream, 80))
            section_id = struct.unpack("<I", _read_exact(stream, 4))[0]
            if tag:
                tags.setdefault(tag, section_id)
                alias = _STATIC_TAG_ALIASES.get(tag)
                if alias:
                    tags.setdefault(alias, section_id)
        return tags

    def _section(self, tag_index: dict[str, int], name: str) -> tuple[_IndexEntry, ...]:
        section_id = tag_index.get(name)
        if section_id is None:
            raise LegacyNicoletError("Legacy Nicolet required technical section is missing.")
        entries = self._section_entries.get(section_id, ())
        if not entries:
            raise LegacyNicoletError("Legacy Nicolet required technical section is missing.")
        return entries

    def _read_ts_channels(self, stream: BinaryIO, tag_index: dict[str, int]) -> list[NicoletChannel]:
        entries = self._section(tag_index, "TSGUID")
        parsed_packets: list[list[NicoletChannel]] = []
        for entry in entries:
            if entry.section_length < 24:
                raise LegacyNicoletError("Legacy Nicolet signal metadata section is truncated.")
            header = self._read_at(stream, entry.offset, 24)
            packet_length = struct.unpack_from("<Q", header, 16)[0]
            if packet_length < 24 or packet_length > _MAX_METADATA_PACKET_BYTES:
                raise LegacyNicoletError("Legacy Nicolet signal metadata is invalid.")
            if packet_length > entry.section_length:
                raise LegacyNicoletError("Legacy Nicolet signal metadata section is truncated.")
            payload = self._read_at(stream, entry.offset + 24, packet_length - 24)
            if len(payload) < 736:
                raise LegacyNicoletError("Legacy Nicolet signal metadata is truncated.")
            element_count = struct.unpack_from("<I", payload, 728)[0]
            if not 0 < element_count <= _MAX_STATIC_PACKETS:
                raise LegacyNicoletError("Legacy Nicolet channel table is invalid.")
            if 736 + element_count * 552 > len(payload):
                raise LegacyNicoletError("Legacy Nicolet channel table is truncated.")

            channels: list[NicoletChannel] = []
            for channel_index in range(element_count):
                offset = 736 + channel_index * 552
                label = _decode_utf16_field(payload[offset : offset + 64])
                sampling_rate = struct.unpack_from("<d", payload, offset + 272)[0]
                scale = struct.unpack_from("<d", payload, offset + 280)[0]
                if (
                    not label
                    or len(label) > 64
                    or not _finite(sampling_rate, positive=True)
                    or not _finite(scale)
                    or scale == 0
                ):
                    raise LegacyNicoletError("Legacy Nicolet channel metadata is invalid.")
                rounded_rate = int(round(sampling_rate))
                if rounded_rate <= 0 or abs(sampling_rate - rounded_rate) > 1e-6:
                    raise LegacyNicoletError("Legacy Nicolet sampling rate is invalid.")
                try:
                    section_id = tag_index[str(channel_index)]
                except KeyError as exc:
                    raise LegacyNicoletError("Legacy Nicolet channel data section is missing.") from exc
                channels.append(NicoletChannel(label, rounded_rate, scale, section_id))
            parsed_packets.append(channels)

        channels = parsed_packets[0]
        for other in parsed_packets[1:]:
            if other != channels:
                raise LegacyNicoletError(
                    "Legacy Nicolet per-segment channel map changes are unsupported."
                )
        return channels

    def _read_segments(self, stream: BinaryIO, tag_index: dict[str, int], target_rate: int) -> tuple[NicoletSegment, ...]:
        entries = self._section(tag_index, "SegmentStream")
        total_bytes = sum(entry.section_length for entry in entries)
        if total_bytes % 152 or total_bytes // 152 > _MAX_SEGMENTS:
            raise LegacyNicoletError("Legacy Nicolet segment table is invalid.")
        segments: list[NicoletSegment] = []
        first_start: float | None = None
        sample_start = 0
        for entry in entries:
            stream.seek(entry.offset)
            for _ in range(entry.section_length // 152):
                start_serial = struct.unpack("<d", _read_exact(stream, 8))[0]
                stream.seek(8, os.SEEK_CUR)
                duration = struct.unpack("<d", _read_exact(stream, 8))[0]
                stream.seek(128, os.SEEK_CUR)
                start_seconds = start_serial * _DAY_SECONDS - _NICOLET_EPOCH_OFFSET
                if (
                    not _finite(start_serial)
                    or not _finite(start_seconds)
                    or not _finite(duration, positive=True)
                    or duration > 7 * 86400
                ):
                    raise LegacyNicoletError("Legacy Nicolet segment timing is invalid.")
                if first_start is None:
                    first_start = start_seconds
                sample_count = int(round(duration * target_rate))
                if sample_count <= 0:
                    raise LegacyNicoletError("Legacy Nicolet segment sample count is invalid.")
                relative_start_seconds = start_seconds - first_start
                if not _finite(relative_start_seconds):
                    raise LegacyNicoletError("Legacy Nicolet segment timing is invalid.")
                segments.append(NicoletSegment(relative_start_seconds, duration, sample_count, sample_start))
                sample_start += sample_count
        if not segments:
            raise LegacyNicoletError("Legacy Nicolet recording has no segments.")
        self._first_segment_start_seconds = first_start if first_start is not None else 0.0
        segment_tuple = tuple(segments)
        total_samples = sum(segment.sample_count for segment in segments)
        if total_samples > _MAX_SIGNAL_SAMPLES:
            raise LegacyNicoletError("Legacy Nicolet recording exceeds the safe sample limit.")
        return segment_tuple

    def _read_events(
        self,
        stream: BinaryIO,
        tag_index: dict[str, int],
        segments: tuple[NicoletSegment, ...],
        sampling_rate: int,
    ) -> tuple[NicoletEvent, ...]:
        event_section_id = tag_index.get("Events")
        if event_section_id is None:
            return ()
        entries = self._section_entries.get(event_section_id, ())
        if not entries:
            return ()
        if sum(entry.section_length for entry in entries) > _MAX_EVENT_SECTION_BYTES:
            raise LegacyNicoletError("Legacy Nicolet event section exceeds the safe size limit.")
        events: list[NicoletEvent] = []
        event_packet_count = 0
        segment_comparisons = 0
        for entry in entries:
            cursor = entry.offset
            end = entry.offset + entry.section_length
            while cursor + 24 <= end:
                header = self._read_at(stream, cursor, 24)
                if header[:16] != _EVENT_PACKET_GUID:
                    if any(header):
                        raise LegacyNicoletError("Legacy Nicolet event section contains an invalid packet.")
                    cursor += len(header)
                    while cursor < end:
                        chunk_size = min(_EVENT_SCAN_CHUNK_BYTES, end - cursor)
                        if any(self._read_at(stream, cursor, chunk_size)):
                            raise LegacyNicoletError(
                                "Legacy Nicolet event section contains an invalid packet."
                            )
                        cursor += chunk_size
                    break
                packet_length = struct.unpack_from("<Q", header, 16)[0]
                if (
                    packet_length < 240
                    or packet_length > _MAX_EVENT_PACKET_BYTES
                    or packet_length > end - cursor
                ):
                    raise LegacyNicoletError("Legacy Nicolet event packet is invalid.")
                if event_packet_count >= _MAX_EVENTS:
                    raise LegacyNicoletError("Legacy Nicolet event count exceeds the safe limit.")
                event_packet_count += 1
                packet = self._read_at(stream, cursor + 24, packet_length - 24)
                if len(packet) < 200:
                    raise LegacyNicoletError("Legacy Nicolet event packet is truncated.")
                event_date = struct.unpack_from("<d", packet, 8)[0]
                event_fraction = struct.unpack_from("<d", packet, 16)[0]
                duration = struct.unpack_from("<d", packet, 24)[0]
                text_length = struct.unpack_from("<Q", packet, 104)[0]
                event_guid = _format_guid(packet[112:128])
                text_payload_bytes = max(0, len(packet) - 240)
                if (
                    not _finite(event_date)
                    or not _finite(event_fraction)
                    or not _finite(duration)
                    or duration < 0
                    or duration > 7 * 86400
                    or text_length * 2 > text_payload_bytes
                ):
                    raise LegacyNicoletError("Legacy Nicolet event timing is invalid.")
                event_time = (
                    event_date * _DAY_SECONDS
                    + event_fraction
                    - _NICOLET_EPOCH_OFFSET
                    - self._first_segment_start_seconds
                )
                if not _finite(event_time):
                    raise LegacyNicoletError("Legacy Nicolet event timing is invalid.")
                for segment in segments:
                    if segment_comparisons >= _MAX_EVENT_SEGMENT_COMPARISONS:
                        raise LegacyNicoletError(
                            "Legacy Nicolet event-to-segment mapping exceeds the safe work limit."
                        )
                    segment_comparisons += 1
                    segment_end = segment.start_seconds + segment.duration_seconds
                    if event_time < segment.start_seconds - 1e-6 or event_time > segment_end + 1e-6:
                        continue
                    local_seconds = min(max(event_time - segment.start_seconds, 0.0), segment.duration_seconds)
                    sample_offset = min(int(round(local_seconds * sampling_rate)), segment.sample_count)
                    duration_samples = min(
                        int(round(duration * sampling_rate)),
                        segment.sample_count - sample_offset,
                    )
                    events.append(
                        NicoletEvent(
                            onset_seconds=segment.start_seconds + local_seconds,
                            duration_seconds=duration_samples / sampling_rate,
                            kind=_EVENT_TYPES.get(event_guid, "other"),
                            text_present=text_length > 0,
                        )
                    )
                    break
                cursor += packet_length
            while cursor < end:
                chunk_size = min(_EVENT_SCAN_CHUNK_BYTES, end - cursor)
                if any(self._read_at(stream, cursor, chunk_size)):
                    raise LegacyNicoletError(
                        "Legacy Nicolet event section contains an invalid packet."
                    )
                cursor += chunk_size
        return tuple(sorted(events, key=lambda event: (event.onset_seconds, event.kind)))

    def read_header(self) -> NicoletHeader:
        """Read safe technical metadata and sanitized embedded event timing."""

        if self._header is not None:
            return self._header
        try:
            with self._open_source() as stream:
                first_fields = _read_exact(stream, 28)
                index_offset = struct.unpack_from("<I", first_fields, 24)[0]
                tag_index = self._read_tags(stream)
                self._section_entries = self._read_indices(stream, index_offset)
                channels = self._read_ts_channels(stream, tag_index)
                rate_counts = Counter(channel.sampling_rate for channel in channels)
                target_rate = max(rate_counts, key=lambda rate: (rate_counts[rate], rate))
                selected = [channel for channel in channels if channel.sampling_rate == target_rate]
                labels = [channel.label for channel in selected]
                if not selected or len(labels) != len(set(labels)):
                    raise LegacyNicoletError("Legacy Nicolet common-rate channels are ambiguous.")
                segments = self._read_segments(stream, tag_index, target_rate)
                total_samples = sum(segment.sample_count for segment in segments)
                events = self._read_events(stream, tag_index, segments, target_rate)
                self._header = NicoletHeader(
                    sampling_rate=target_rate,
                    channels=tuple(selected),
                    segments=segments,
                    total_samples=total_samples,
                    events=events,
                )
                return self._header
        except LegacyNicoletError:
            raise
        except (OSError, EOFError, struct.error, ValueError, OverflowError) as exc:
            raise LegacyNicoletError("Legacy Nicolet file is unreadable or malformed.") from exc

    def _read_channel_samples(
        self,
        stream: BinaryIO,
        channel: NicoletChannel,
        total_samples: int,
    ) -> np.ndarray:
        entries = self._section_entries.get(channel.section_id, ())
        if not entries:
            raise LegacyNicoletError("Legacy Nicolet channel data section is missing.")
        sections: list[tuple[int, int, int]] = []
        cursor = 0
        for entry in entries:
            if entry.section_length % 2:
                raise LegacyNicoletError("Legacy Nicolet signal section is malformed.")
            count = entry.section_length // 2
            sections.append((cursor, cursor + count, entry.offset))
            cursor += count
        if cursor < total_samples:
            raise LegacyNicoletError("Legacy Nicolet signal data is incomplete.")

        output = np.empty(total_samples, dtype=np.float32)
        for start, end, offset in sections:
            left = max(0, start)
            right = min(total_samples, end)
            if right <= left:
                continue
            sample_count = right - left
            stream.seek(offset + (left - start) * 2)
            data = np.frombuffer(_read_exact(stream, sample_count * 2), dtype="<i2").astype(np.float32)
            data *= channel.scale
            if not np.isfinite(data).all():
                raise LegacyNicoletError("Legacy Nicolet signal data is non-finite.")
            output[left:right] = data
        return output

    def read_data(self) -> tuple[np.ndarray, int, list[str]]:
        """Read the reviewed bipolar montage as ``(channels, samples)``."""

        header = self.read_header()
        _validate_segment_continuity(header.segments, header.sampling_rate)
        signals: np.ndarray
        labels: list[str]
        if header.sampling_rate == MODEL_SAMPLING_RATE:
            selected = select_model_channels(header)
            signals = np.empty((len(selected), header.total_samples), dtype=np.float32)
            with self._open_source() as stream:
                for index, channel in enumerate(selected):
                    signals[index] = self._read_channel_samples(
                        stream, channel, header.total_samples
                    )
            labels = list(MODEL_CHANNELS)
            sampling_rate = MODEL_SAMPLING_RATE
        elif header.sampling_rate == LEGACY_SOURCE_SAMPLING_RATE:
            montage = select_legacy_montage_channels(header)
            source_channels = {channel for _, left, right in montage for channel in (left, right)}
            with self._open_source() as stream:
                source_signals = {
                    channel: self._read_channel_samples(stream, channel, header.total_samples)
                    for channel in source_channels
                }
            signals = np.empty((len(montage), header.total_samples), dtype=np.float32)
            for index, (_, left, right) in enumerate(montage):
                np.subtract(source_signals[left], source_signals[right], out=signals[index])
            del source_signals
            signals = resample_poly(
                signals,
                _LEGACY_RESAMPLE_UP,
                _LEGACY_RESAMPLE_DOWN,
                axis=1,
                window=("kaiser", 5.0),
            )
            labels = list(MODEL_CHANNELS)
            sampling_rate = MODEL_SAMPLING_RATE
        else:
            raise LegacyNicoletError("Legacy Nicolet source sampling rate is unsupported.")
        if not np.isfinite(signals).all():
            raise LegacyNicoletError("Legacy Nicolet signal data is non-finite.")
        return cast(np.ndarray, signals.astype(np.float32, copy=False)), sampling_rate, labels


def select_model_channels(header: NicoletHeader) -> tuple[NicoletChannel, ...]:
    """Select the exact reviewed 18-channel EEG contract."""

    if header.sampling_rate != MODEL_SAMPLING_RATE:
        raise LegacyNicoletError("Legacy Nicolet sampling rate does not match the model contract.")
    channels_by_label = {channel.label: channel for channel in header.channels}
    if len(channels_by_label) != len(header.channels):
        raise LegacyNicoletError("Legacy Nicolet model channels are ambiguous.")
    try:
        selected = tuple(channels_by_label[label] for label in MODEL_CHANNELS)
    except KeyError as exc:
        raise LegacyNicoletError("Legacy Nicolet input is missing a required model channel.") from exc
    if any(channel.sampling_rate != MODEL_SAMPLING_RATE for channel in selected):
        raise LegacyNicoletError("Legacy Nicolet model channels do not share the required sampling rate.")
    return selected


def validate_legacy_nicolet(path: str | Path) -> NicoletHeader:
    """Validate a legacy Nicolet file without materializing signal samples."""

    return LegacyNicoletReader(path).read_header()


def read_uniform_legacy_nicolet(path: str | Path) -> tuple[np.ndarray, int, list[str]]:
    """Read a legacy Nicolet file using its common-rate EEG channels."""

    return LegacyNicoletReader(path).read_data()


def read_legacy_nicolet_events(path: str | Path) -> tuple[NicoletEvent, ...]:
    """Return sanitized embedded event timing without raw labels or text."""

    return LegacyNicoletReader(path).read_header().events
