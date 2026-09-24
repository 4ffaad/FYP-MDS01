"""EDF/Nicolet EEG compatibility and privacy tests."""

from __future__ import annotations

import os
from pathlib import Path
import struct
import tempfile
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np

from backend.app.eeg.io import (
    detect_eeg_format,
    read_legacy_eeg_events,
    read_uniform_eeg,
    validate_nicolet,
    validate_legacy_nicolet_e,
)
from backend.app.eeg.contracts import MODEL_CHANNELS, MODEL_SAMPLING_RATE
from backend.app.eeg.legacy_nicolet import (
    LegacyNicoletError,
    LegacyNicoletReader,
    NicoletChannel,
    NicoletSegment,
    NicoletHeader,
    _EVENT_PACKET_GUID,
    _IndexEntry,
    select_legacy_montage_channels,
    select_model_channels,
)
from backend.app.privacy.deidentify import (
    deidentify_legacy_nicolet,
    deidentify_nicolet,
    inspect_metadata,
)
from backend.app.services.validation_service import validate_eeg


class NicoletFormatTests(unittest.TestCase):
    """Exercise the real MNE Nicolet reader against synthetic private data."""

    @staticmethod
    def _write_nicolet(root: Path, *, channels: list[str] | None = None, samples: int = 1024) -> Path:
        channels = channels or ["FP1-F7", "F7-T7"]
        stem = root / "recording"
        header = "\n".join(
            [
                f"elec_names=[{','.join(channels)}]",
                "sample_freq=256",
                f"num_channels={len(channels)}",
                f"num_samples={samples}",
                "conversion_factor=1",
                "start_ts=2020-01-01 00:00:00.000",
                "rec_id=1",
                "adm_id=2",
                "pat_id=3",
            ]
        ) + "\n"
        values = np.arange(samples * len(channels), dtype="<i2").reshape(samples, len(channels))
        stem.with_suffix(".head").write_text(header, encoding="utf-8")
        stem.with_suffix(".data").write_bytes(values.tobytes())
        return stem.with_suffix(".data")

    def test_nicolet_validation_and_reading_share_safe_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_nicolet(Path(directory))

            metadata = validate_nicolet(path)
            generic = validate_eeg(path)
            signals, sampling_rate, labels = read_uniform_eeg(path)

            self.assertEqual(metadata.format, "nicolet")
            self.assertEqual(generic["format"], "nicolet")
            self.assertEqual(sampling_rate, 256)
            self.assertEqual(labels, ["FP1-F7", "F7-T7"])
            self.assertEqual(signals.shape, (2, 1024))
            self.assertTrue(np.isfinite(signals).all())

    def test_nicolet_requires_matching_head_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.data"
            path.write_bytes(b"not a complete recording")

            with self.assertRaisesRegex(ValueError, "matching .head"):
                validate_nicolet(path)

    def test_nicolet_rejects_over_budget_signal_before_preloading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_nicolet(Path(directory), samples=3)
            raw = Mock()
            raw.info = {"sfreq": 256.0}
            raw.ch_names = ["FP1-F7", "F7-T7"]
            raw.n_times = 3
            raw.get_data.side_effect = AssertionError("signal data was materialized")

            with (
                patch("backend.app.eeg.io._MAX_NICOLET_SIGNAL_VALUES", 5, create=True),
                patch("backend.app.eeg.io._read_nicolet", return_value=raw) as open_raw,
            ):
                with self.assertRaisesRegex(ValueError, "safe signal-size limit"):
                    read_uniform_eeg(path)

            open_raw.assert_called_once_with(path, preload=False)
            raw.get_data.assert_not_called()
            raw.close.assert_called_once()

    def test_nicolet_validation_rejects_over_budget_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_nicolet(Path(directory), samples=3)
            raw = Mock()
            raw.info = {"sfreq": 256.0}
            raw.ch_names = ["FP1-F7", "F7-T7"]
            raw.n_times = 3

            with (
                patch("backend.app.eeg.io._MAX_NICOLET_SIGNAL_VALUES", 5, create=True),
                patch("backend.app.eeg.io._read_nicolet", return_value=raw),
            ):
                with self.assertRaisesRegex(ValueError, "unreadable or malformed"):
                    validate_nicolet(path)

            raw.load_data.assert_not_called()
            raw.close.assert_called_once()

    def test_nicolet_deidentification_uses_preload_size_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._write_nicolet(root, samples=3)
            output = root / "scrubbed.edf"
            raw = Mock()
            raw.info = {"sfreq": 256.0}
            raw.ch_names = ["FP1-F7", "F7-T7"]
            raw.n_times = 3

            with (
                patch("backend.app.eeg.io._MAX_NICOLET_SIGNAL_VALUES", 5),
                patch("backend.app.eeg.io._read_nicolet", return_value=raw),
            ):
                with self.assertRaisesRegex(ValueError, "safe signal-size limit"):
                    deidentify_nicolet(path, output, "REC-SYNTHETIC")

            raw.load_data.assert_not_called()
            raw.get_data.assert_not_called()
            raw.close.assert_called_once()
            self.assertFalse(output.exists())

    def test_legacy_nicolet_channel_packet_stays_within_indexed_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            payload = bytearray(736 + 552)
            struct.pack_into("<I", payload, 728, 1)
            payload[736:800] = "FP1".encode("utf-16-le").ljust(64, b"\x00")
            struct.pack_into("<d", payload, 736 + 272, 500.0)
            struct.pack_into("<d", payload, 736 + 280, 1.0)
            packet = b"\x00" * 16 + struct.pack("<Q", len(payload) + 24) + payload
            packet_and_following_section = packet + b"\x00" * 24
            path.write_bytes(packet_and_following_section)
            reader = LegacyNicoletReader(path)
            reader._section_entries[7] = (_IndexEntry(7, 0, len(packet) - 1),)

            with self.assertRaisesRegex(LegacyNicoletError, "section"):
                reader._read_ts_channels(
                    BytesIO(packet_and_following_section), {"TSGUID": 7, "0": 8}
                )

            reader._section_entries[7] = (_IndexEntry(7, 0, len(packet)),)
            channels = reader._read_ts_channels(
                BytesIO(packet_and_following_section), {"TSGUID": 7, "0": 8}
            )

        self.assertEqual([channel.label for channel in channels], ["FP1"])

    def test_legacy_nicolet_rejects_per_segment_channel_map_changes(self) -> None:
        def packet(label: str) -> bytes:
            payload = bytearray(736 + 552)
            struct.pack_into("<I", payload, 728, 1)
            payload[736:800] = label.encode("utf-16-le").ljust(64, b"\x00")
            struct.pack_into("<d", payload, 736 + 272, 500.0)
            struct.pack_into("<d", payload, 736 + 280, 1.0)
            return b"\x00" * 16 + struct.pack("<Q", len(payload) + 24) + payload

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            first = packet("FP1")
            second = packet("FP2")
            path.write_bytes(first + second)
            reader = LegacyNicoletReader(path)
            reader._section_entries[7] = (
                _IndexEntry(7, 0, len(first)),
                _IndexEntry(7, len(first), len(second)),
            )

            with self.assertRaisesRegex(
                LegacyNicoletError, "per-segment channel map changes are unsupported"
            ):
                reader._read_ts_channels(BytesIO(first + second), {"TSGUID": 7, "0": 8})

    def test_legacy_nicolet_rejects_segment_gaps_and_overlaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"synthetic source")
            reader = LegacyNicoletReader(path)
            entry = _IndexEntry(1, 0, 304)
            reader._section = Mock(return_value=(entry,))

            contiguous = BytesIO()
            for start_seconds in (0.0, 1.0):
                serial_date = 25569 + start_seconds / 86400
                contiguous.write(
                    np.asarray([serial_date], dtype="<f8").tobytes()
                    + b"\x00" * 8
                    + np.asarray([1.0], dtype="<f8").tobytes()
                    + b"\x00" * 128
                )
            segments = reader._read_segments(contiguous, {}, 500)
            self.assertEqual([segment.sample_start for segment in segments], [0, 500])

            for second_start in (1.02, 0.98):
                with self.subTest(second_start=second_start):
                    stream = BytesIO()
                    for start_seconds in (0.0, second_start):
                        serial_date = 25569 + start_seconds / 86400
                        stream.write(
                            np.asarray([serial_date], dtype="<f8").tobytes()
                            + b"\x00" * 8
                            + np.asarray([1.0], dtype="<f8").tobytes()
                            + b"\x00" * 128
                        )
                    segments = reader._read_segments(stream, {}, 500)
                    self.assertAlmostEqual(segments[1].start_seconds, second_start, places=5)
                    header = NicoletHeader(
                        sampling_rate=MODEL_SAMPLING_RATE,
                        channels=(),
                        segments=(
                            NicoletSegment(0.0, 1.0, 256, 0),
                            NicoletSegment(second_start, 1.0, 256, 256),
                        ),
                        total_samples=512,
                        events=(),
                    )
                    reader._header = header
                    reader._open_source = Mock()
                    with self.assertRaisesRegex(
                        LegacyNicoletError, "segments are discontinuous"
                    ):
                        reader.read_data()
                    reader._open_source.assert_not_called()
                    with patch(
                        "backend.app.eeg.io.validate_legacy_nicolet",
                        return_value=header,
                    ):
                        with self.assertRaisesRegex(ValueError, "unreadable or malformed"):
                            validate_legacy_nicolet_e(path)

    def test_legacy_nicolet_rejects_overflowing_serial_start_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"synthetic source")
            reader = LegacyNicoletReader(path)
            entry = _IndexEntry(1, 0, 152)
            reader._section = Mock(return_value=(entry,))
            stream = BytesIO(
                struct.pack("<d", 1e308)
                + b"\x00" * 8
                + struct.pack("<d", 1.0)
                + b"\x00" * 128
            )

            with self.assertRaisesRegex(LegacyNicoletError, "segment timing is invalid"):
                reader._read_segments(stream, {}, 500)

    def test_legacy_nicolet_rejects_overflowing_relative_segment_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"synthetic source")
            reader = LegacyNicoletReader(path)
            entry = _IndexEntry(1, 0, 304)
            reader._section = Mock(return_value=(entry,))
            first_record = (
                struct.pack("<d", 1.05e303)
                + b"\x00" * 8
                + struct.pack("<d", 1.0)
                + b"\x00" * 128
            )
            second_record = (
                struct.pack("<d", -1.05e303)
                + b"\x00" * 8
                + struct.pack("<d", 1.0)
                + b"\x00" * 128
            )
            stream = BytesIO(first_record + second_record)

            with self.assertRaisesRegex(LegacyNicoletError, "segment timing is invalid"):
                reader._read_segments(stream, {}, 500)

    def test_legacy_nicolet_event_timing_preserves_segment_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            payload = bytearray(240)
            struct.pack_into("<d", payload, 8, 25569.0)
            struct.pack_into("<d", payload, 16, 2.25)
            struct.pack_into("<d", payload, 24, 0.5)
            packet = _EVENT_PACKET_GUID + struct.pack("<Q", 264) + payload
            path.write_bytes(packet)
            reader = LegacyNicoletReader(path)
            reader._first_segment_start_seconds = 0.0
            segments = (
                NicoletSegment(0.0, 1.0, 500, 0),
                NicoletSegment(2.0, 1.0, 500, 500),
            )
            reader._section_entries[12] = (_IndexEntry(12, 0, len(packet)),)

            events = reader._read_events(
                BytesIO(packet), {"Events": 12}, segments, 500
            )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].onset_seconds, 2.25)
        self.assertEqual(events[0].duration_seconds, 0.5)

    def test_legacy_nicolet_rejects_overflowing_event_serial_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            payload = bytearray(240)
            struct.pack_into("<d", payload, 8, 1e308)
            struct.pack_into("<d", payload, 16, 0.0)
            struct.pack_into("<d", payload, 24, 0.5)
            packet = _EVENT_PACKET_GUID + struct.pack("<Q", 264) + payload
            path.write_bytes(packet)
            reader = LegacyNicoletReader(path)
            reader._first_segment_start_seconds = 0.0
            reader._section_entries[12] = (_IndexEntry(12, 0, len(packet)),)
            segments = (NicoletSegment(0.0, 1.0, 500, 0),)

            with self.assertRaisesRegex(LegacyNicoletError, "event timing is invalid"):
                reader._read_events(BytesIO(packet), {"Events": 12}, segments, 500)

    def test_legacy_nicolet_event_padding_is_scanned_in_bounded_chunks(self) -> None:
        class TrackingStream(BytesIO):
            def __init__(self, payload: bytes) -> None:
                super().__init__(payload)
                self.read_sizes: list[int | None] = []

            def read(self, size: int | None = -1) -> bytes:
                self.read_sizes.append(size)
                return super().read(size)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            padding = b"\x00" * (128 * 1024 + 37)
            path.write_bytes(padding)
            reader = LegacyNicoletReader(path)
            reader._section_entries[12] = (_IndexEntry(12, 0, len(padding)),)
            stream = TrackingStream(padding)

            events = reader._read_events(stream, {"Events": 12}, (), 256)

        self.assertEqual(events, ())
        self.assertTrue(stream.read_sizes)
        self.assertTrue(
            all(size is not None and size <= 64 * 1024 for size in stream.read_sizes)
        )

    def test_legacy_nicolet_rejects_nonzero_short_event_section_tail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            tail = b"\x00" * 22 + b"\x01"
            path.write_bytes(tail)
            reader = LegacyNicoletReader(path)
            reader._section_entries[12] = (_IndexEntry(12, 0, len(tail)),)

            with self.assertRaisesRegex(LegacyNicoletError, "invalid packet"):
                reader._read_events(BytesIO(tail), {"Events": 12}, (), 256)

    def test_legacy_nicolet_event_sections_have_an_aggregate_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"\x00" * 48)
            reader = LegacyNicoletReader(path)
            reader._section_entries[12] = (
                _IndexEntry(12, 0, 24),
                _IndexEntry(12, 24, 24),
            )
            stream = BytesIO(b"\x00" * 48)

            with patch(
                "backend.app.eeg.legacy_nicolet._MAX_EVENT_SECTION_BYTES",
                47,
            ):
                with self.assertRaisesRegex(
                    LegacyNicoletError, "event section exceeds the safe size limit"
                ):
                    reader._read_events(stream, {"Events": 12}, (), 256)

        self.assertEqual(stream.tell(), 0)

    def test_legacy_nicolet_packet_limit_counts_events_outside_segments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            payload = bytearray(240)
            struct.pack_into("<d", payload, 8, 25569.0)
            struct.pack_into("<d", payload, 16, 2.25)
            packet = _EVENT_PACKET_GUID + struct.pack("<Q", 264) + payload
            path.write_bytes(packet * 2)
            reader = LegacyNicoletReader(path)
            reader._section_entries[12] = (_IndexEntry(12, 0, len(packet) * 2),)
            segments = (NicoletSegment(100.0, 1.0, 256, 0),)

            with patch("backend.app.eeg.legacy_nicolet._MAX_EVENTS", 1):
                with self.assertRaisesRegex(
                    LegacyNicoletError, "event count exceeds the safe limit"
                ):
                    reader._read_events(BytesIO(packet * 2), {"Events": 12}, segments, 256)

    def test_legacy_nicolet_bounds_event_to_segment_mapping_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            payload = bytearray(240)
            struct.pack_into("<d", payload, 8, 25569.0)
            struct.pack_into("<d", payload, 16, 2.25)
            struct.pack_into("<d", payload, 24, 0.5)
            packet = _EVENT_PACKET_GUID + struct.pack("<Q", 264) + payload
            path.write_bytes(packet)
            reader = LegacyNicoletReader(path)
            reader._first_segment_start_seconds = 0.0
            reader._section_entries[12] = (_IndexEntry(12, 0, len(packet)),)
            segments = tuple(
                NicoletSegment(float(start), 1.0, 256, index * 256)
                for index, start in enumerate((100, 200, 300))
            )

            with patch(
                "backend.app.eeg.legacy_nicolet._MAX_EVENT_SEGMENT_COMPARISONS",
                2,
                create=True,
            ):
                with self.assertRaisesRegex(
                    LegacyNicoletError, "event-to-segment mapping exceeds"
                ):
                    reader._read_events(BytesIO(packet), {"Events": 12}, segments, 256)

    def test_nicolet_rejects_symlinked_data_and_head_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "source"
            source_root.mkdir()
            source = self._write_nicolet(source_root)
            linked = root / "linked.data"
            linked_head = linked.with_suffix(".head")
            linked.symlink_to(source)
            linked_head.symlink_to(source.with_suffix(".head"))

            with self.assertRaisesRegex(ValueError, "symlink"):
                detect_eeg_format(linked)

            linked_head_data = root / "linked-head.data"
            linked_head_data.write_bytes(source.read_bytes())
            linked_head_data.with_suffix(".head").symlink_to(source.with_suffix(".head"))
            with self.assertRaisesRegex(ValueError, "symlink"):
                detect_eeg_format(linked_head_data)

    def test_legacy_nicolet_e_is_detected_without_a_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"legacy nicolet placeholder")

            self.assertEqual(detect_eeg_format(path), "nicolet-e")

    def test_legacy_nicolet_selects_only_the_reviewed_model_channels(self) -> None:
        header = NicoletHeader(
            sampling_rate=MODEL_SAMPLING_RATE,
            channels=tuple(
                NicoletChannel(label, MODEL_SAMPLING_RATE, 1.0, index)
                for index, label in enumerate((*MODEL_CHANNELS, "EKG"))
            ),
            segments=(),
            total_samples=0,
            events=(),
        )

        selected = select_model_channels(header)

        self.assertEqual(tuple(channel.label for channel in selected), MODEL_CHANNELS)
        with self.assertRaises(LegacyNicoletError):
            select_model_channels(
                NicoletHeader(
                    sampling_rate=MODEL_SAMPLING_RATE,
                    channels=header.channels[:-2],
                    segments=(),
                    total_samples=0,
                    events=(),
                )
            )

    def test_legacy_500_hz_referential_montage_derives_reviewed_bipolar_channels(self) -> None:
        source_labels = [
            "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
            "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz",
        ]
        header = NicoletHeader(
            sampling_rate=500,
            channels=tuple(
                NicoletChannel(label, 500, 1.0, index)
                for index, label in enumerate(source_labels)
            ),
            segments=(),
            total_samples=0,
            events=(),
        )

        montage = select_legacy_montage_channels(header)

        self.assertEqual(tuple(item[0] for item in montage), MODEL_CHANNELS)
        self.assertEqual(montage[1][1].label, "F7")
        self.assertEqual(montage[1][2].label, "T3")
        with self.assertRaises(LegacyNicoletError):
            select_legacy_montage_channels(
                NicoletHeader(
                    sampling_rate=500,
                    channels=header.channels[:-1],
                    segments=(),
                    total_samples=0,
                    events=(),
                )
            )

    def test_legacy_channel_samples_use_float32_to_bound_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(np.asarray([2, -4, 6], dtype="<i2").tobytes())
            reader = LegacyNicoletReader(path)
            reader._section_entries[7] = (_IndexEntry(7, 0, 6),)

            samples = reader._read_channel_samples(
                BytesIO(path.read_bytes()),
                NicoletChannel("FP1", 500, 0.25, 7),
                3,
            )

        self.assertEqual(samples.dtype, np.float32)
        np.testing.assert_array_equal(samples, np.asarray([0.5, -1.0, 1.5], dtype=np.float32))

    def test_legacy_500_hz_conversion_returns_contract_channels_as_float32(self) -> None:
        source_labels = [
            "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
            "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz",
        ]
        stream_bytes = bytearray()
        sections: dict[int, tuple[_IndexEntry, ...]] = {}
        for section_id in range(len(source_labels)):
            samples = np.asarray(
                [section_id + offset for offset in range(4)], dtype="<i2"
            )
            start = len(stream_bytes)
            stream_bytes.extend(samples.tobytes())
            sections[section_id] = (_IndexEntry(section_id, start, samples.nbytes),)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.e"
            path.write_bytes(b"synthetic source")
            reader = LegacyNicoletReader(path)
            reader._header = NicoletHeader(
                sampling_rate=500,
                channels=tuple(
                    NicoletChannel(label, 500, 1.0, section_id)
                    for section_id, label in enumerate(source_labels)
                ),
                segments=(),
                total_samples=4,
                events=(),
            )
            reader._section_entries = sections
            with patch.object(
                reader,
                "_open_source",
                side_effect=lambda: BytesIO(stream_bytes),
            ):
                signals, sampling_rate, labels = reader.read_data()

        self.assertEqual(signals.dtype, np.float32)
        self.assertEqual(signals.shape, (len(MODEL_CHANNELS), 3))
        self.assertEqual(sampling_rate, MODEL_SAMPLING_RATE)
        self.assertEqual(labels, list(MODEL_CHANNELS))

    def test_legacy_nicolet_deidentification_writes_the_model_contract(self) -> None:
        signals = np.zeros((len(MODEL_CHANNELS), 2048), dtype=np.float64)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "scrubbed.edf"
            with patch(
                "backend.app.eeg.io.read_uniform_legacy_eeg",
                return_value=(signals, MODEL_SAMPLING_RATE, list(MODEL_CHANNELS)),
            ):
                deidentify_legacy_nicolet(Path(directory) / "recording.e", output, "REC-TEST")

            self.assertTrue(inspect_metadata(str(output))["is_deidentified"])

    def test_legacy_nicolet_malformed_file_has_a_generic_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patient-secret.e"
            path.write_bytes(b"not a legacy Nicolet file")

            with self.assertRaisesRegex(ValueError, "unreadable or malformed") as caught:
                validate_eeg(path)
            self.assertNotIn("patient-secret", str(caught.exception))

    def test_legacy_nicolet_public_fixture_pipeline_when_configured(self) -> None:
        fixture = Path(
            os.environ.get(
                "MDS01_LEGACY_NICOLET_FIXTURE",
                "/tmp/mds01-nicolet-reader/@NicoletFile/janbrogger.e",
            )
        )
        if not fixture.is_file():
            self.skipTest("Set MDS01_LEGACY_NICOLET_FIXTURE to run the public .e fixture regression.")
        header = LegacyNicoletReader(fixture).read_header()
        events = read_legacy_eeg_events(fixture)

        self.assertEqual(header.sampling_rate, 256)
        self.assertEqual(len(header.channels), 24)
        self.assertGreater(len(events), 0)
        with self.assertRaisesRegex(ValueError, "unreadable or malformed"):
            validate_legacy_nicolet_e(fixture)

    def test_nicolet_parser_errors_do_not_echo_header_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "recording.data"
            path.write_bytes(b"not a real recording")
            path.with_suffix(".head").write_text(
                "elec_names=[FP1-F7]\n"
                "sample_freq=256\n"
                "num_channels=1\n"
                "num_samples=1\n"
                "conversion_factor=1\n"
                "start_ts=2020-01-01 00:00:00.000\n"
                "rec_id=patient-secret\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unreadable or malformed") as caught:
                validate_eeg(path)
            self.assertNotIn("patient-secret", str(caught.exception))

    def test_nicolet_deidentifies_to_verified_scrubbed_edf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_nicolet(root)
            output = root / "scrubbed" / "recording.edf"

            deidentify_nicolet(source, output, "REC-SYNTHETIC")
            metadata = inspect_metadata(str(output))
            signals, sampling_rate, labels = read_uniform_eeg(output)

            self.assertTrue(output.is_file())
            self.assertTrue(metadata["is_deidentified"])
            self.assertEqual(sampling_rate, 256)
            self.assertEqual(labels, ["FP1-F7", "F7-T7"])
            self.assertEqual(signals.shape, (2, 1024))
            self.assertTrue(np.isfinite(signals).all())


if __name__ == "__main__":
    unittest.main()
