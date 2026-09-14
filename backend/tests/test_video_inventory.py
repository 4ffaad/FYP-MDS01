"""Video inventory compatibility checks."""

from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from backend.scripts.video_inventory import inventory


class VideoInventoryTests(unittest.TestCase):
    def test_inventory_accepts_opencv_without_set_log_level(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("sys.modules", {"cv2": types.SimpleNamespace()}):
            result = inventory(Path(directory))
        self.assertEqual(result["video_count"], 0)


if __name__ == "__main__":
    unittest.main()
