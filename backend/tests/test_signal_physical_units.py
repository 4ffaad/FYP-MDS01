"""Regression coverage for source physical-unit calibration."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.signal_service import (
    SignalPreviewUnavailable,
    _apply_source_display_filter,
    _source_preview,
    _edf_volts_per_unit,
)


class SignalPhysicalUnitTests(unittest.TestCase):
    def test_supported_edf_units_convert_to_si_volts(self) -> None:
        for dimension, expected in (
            ("V", 1.0),
            ("mV", 1e-3),
            ("uV", 1e-6),
            ("µV", 1e-6),
            ("μV", 1e-6),
            ("nV", 1e-9),
        ):
            with self.subTest(dimension=dimension):
                self.assertEqual(_edf_volts_per_unit(dimension), expected)

    def test_unknown_edf_unit_fails_closed(self) -> None:
        with self.assertRaises(SignalPreviewUnavailable):
            _edf_volts_per_unit("counts")

    def test_source_filter_uses_native_rate_and_splits_acquisition_gaps(self) -> None:
        import numpy as np

        rate = 500
        time = np.concatenate(
            (np.arange(0, 12, 1 / rate), np.arange(15, 27, 1 / rate))
        )
        signal = np.sin(2 * np.pi * 10 * time) + np.sin(2 * np.pi * 50 * time)
        payload = {
            "sampling_rate": rate,
            "time_seconds": time.tolist(),
            "channels": [
                {"label": "FP1", "sampling_rate": rate, "samples": signal.tolist()}
            ],
        }

        self.assertTrue(_apply_source_display_filter(payload))
        filtered = np.asarray(payload["channels"][0]["samples"])
        # Skip each 2-second filter edge and verify the retained 10 Hz signal
        # with the 50 Hz line component removed on both sides of the gap.
        for sample_slice in (slice(1000, 5000), slice(7000, 11000)):
            with self.subTest(sample_slice=sample_slice):
                expected_10hz = np.sin(2 * np.pi * 10 * time[sample_slice])
                self.assertLess(
                    np.sqrt(
                        np.mean((filtered[sample_slice] - expected_10hz) ** 2)
                    ),
                    0.1,
                )

    def test_source_filter_leaves_low_rate_trends_untouched(self) -> None:
        import numpy as np

        samples = [1.0, 2.0, 3.0]
        payload = {
            "sampling_rate": 1,
            "time_seconds": [0.0, 1.0, 2.0],
            "channels": [
                {"label": "Rate", "sampling_rate": 1, "samples": samples[:]}
            ],
        }

        self.assertFalse(_apply_source_display_filter(payload))
        self.assertEqual(payload["channels"][0]["samples"], samples)

    def test_legacy_nicolet_source_range_is_normalized_from_microvolts_to_volts(self) -> None:
        microvolts_per_count = 0.152587890625
        with TemporaryDirectory() as directory:
            temporary_source = Path(directory) / "source.e"
            temporary_source.write_bytes(b"synthetic Nicolet source")

            class Storage:
                def materialize_retained_artifact(self, *_args, **_kwargs):
                    return temporary_source

            parser_payload = {
                "channels": [
                    {
                        "label": "FP1",
                        "samples": [1000 * microvolts_per_count, -500 * microvolts_per_count],
                        "time_seconds": [7200.0, 7200.002],
                        "sampling_rate": 500,
                    }
                ],
                "time_seconds": [7200.0, 7200.002],
                "segments": [
                    {"source_start_seconds": 7200.0, "source_end_seconds": 7212.0}
                ],
                "sampling_rate": 500,
                "display_filter": None,
            }
            with patch(
                "backend.app.eeg.legacy_nicolet.LegacyNicoletReader.read_source_range",
                return_value=parser_payload,
            ):
                preview = _source_preview(
                    SimpleNamespace(session_id="test-session"),
                    SimpleNamespace(
                        record_id="test-record",
                        original_artifact_path="record.source.e.enc",
                    ),
                    Storage(),
                    7200.0,
                    12.0,
                    10_000,
                )

        self.assertEqual(preview["representation"], "original-source")
        self.assertEqual(
            preview["channels"][0]["samples"],
            [1000 * microvolts_per_count * 1e-6, -500 * microvolts_per_count * 1e-6],
        )

    def test_source_preview_omits_timestamps_repeated_by_every_channel(self) -> None:
        shared_times = [7200.0, 7200.002]
        payload = {
            "channels": [
                {"label": "Fp1", "samples": [1.0, 2.0], "time_seconds": shared_times,
                 "sampling_rate": 500},
                {"label": "F7", "samples": [3.0, 4.0], "time_seconds": shared_times[:],
                 "sampling_rate": 500},
                {"label": "ECG", "samples": [5.0, 6.0], "time_seconds": [7200.0, 7200.004],
                 "sampling_rate": 250},
            ],
            "time_seconds": shared_times,
            "segments": [{"source_start_seconds": 7200.0, "source_end_seconds": 7200.01}],
            "sampling_rate": 500,
            "display_filter": None,
        }
        with TemporaryDirectory() as directory:
            temporary_source = Path(directory) / "source.e"
            temporary_source.write_bytes(b"synthetic Nicolet source")

            class Storage:
                def materialize_retained_artifact(self, *_args, **_kwargs):
                    return temporary_source

            with patch(
                "backend.app.eeg.legacy_nicolet.LegacyNicoletReader.read_source_range",
                return_value=payload,
            ):
                preview = _source_preview(
                    SimpleNamespace(session_id="test-session"),
                    SimpleNamespace(
                        record_id="test-record",
                        original_artifact_path="record.source.e.enc",
                    ),
                    Storage(),
                    7200.0,
                    12.0,
                    10_000,
                )

        self.assertEqual(preview["time_seconds"], shared_times)
        self.assertNotIn("time_seconds", preview["channels"][0])
        self.assertNotIn("time_seconds", preview["channels"][1])
        self.assertEqual(preview["channels"][2]["time_seconds"], [7200.0, 7200.004])


if __name__ == "__main__":
    unittest.main()
