"""Regression tests for source-clock gaps in legacy Nicolet files."""

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from backend.app.eeg.legacy_nicolet import (
    LegacyNicoletReader,
    NicoletHeader,
    NicoletSegment,
)


class LegacyNicoletGapTests(unittest.TestCase):
    def test_range_inside_a_source_gap_returns_an_empty_interval(self) -> None:
        header = NicoletHeader(
            sampling_rate=500,
            channels=(),
            segments=(
                NicoletSegment(0.0, 12.0, 6000, 0),
                NicoletSegment(24.0, 12.0, 6000, 6000),
            ),
            total_samples=12000,
            events=(),
        )
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.e"
            source.write_bytes(b"test")
            reader = LegacyNicoletReader(source)
            with patch.object(reader, "read_header", return_value=header):
                result = reader.read_source_range(12.0, 24.0, 10_000)

        self.assertEqual(result["channels"], [])
        self.assertEqual(result["time_seconds"], [])
        self.assertEqual(result["segments"], [])
        self.assertEqual(result["sampling_rate"], 500)
        self.assertIsNone(result["display_filter"])


if __name__ == "__main__":
    unittest.main()
