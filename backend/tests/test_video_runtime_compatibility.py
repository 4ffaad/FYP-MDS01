"""Regression tests for the pinned video runtime's compatibility boundary."""

from __future__ import annotations

import unittest
from pathlib import Path
import os
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from backend.app.video_detection.contract import DetectionError
from backend.app.video_detection.runtime import (
    _adapt_pinned_vsvig_source,
    _configure_torch_backend,
    module_from_file,
)


class VideoRuntimeCompatibilityTests(unittest.TestCase):
    def test_adapts_only_the_pinned_timm_registry_import(self) -> None:
        source = (
            "from timm.models.registry import register_model\n"
            "from torch import nn\n"
        )

        adapted = _adapt_pinned_vsvig_source(source)

        self.assertEqual(adapted.count("from timm.models import register_model"), 1)
        self.assertNotIn("timm.models.registry", adapted)
        self.assertIn("from torch import nn", adapted)

    def test_fails_closed_if_the_expected_upstream_import_changes(self) -> None:
        for source in (
            "from timm.models import register_model\n",
            "from timm.models.registry import register_model\n"
            "from timm.models.registry import register_model\n",
        ):
            with self.subTest(source=source), self.assertRaises(DetectionError):
                _adapt_pinned_vsvig_source(source)

    def test_loader_applies_import_compatibility_without_rewriting_verified_source(self) -> None:
        register_model = object()
        timm = ModuleType("timm")
        timm_models = ModuleType("timm.models")
        setattr(timm, "models", timm_models)
        setattr(timm_models, "register_model", register_model)
        original = "from timm.models.registry import register_model\nloaded = True\n"
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "vsvig"
            source_root.mkdir()
            source_path = source_root / "VSViG.py"
            source_path.write_text(original, encoding="utf-8")
            with patch.dict(sys.modules, {"timm": timm, "timm.models": timm_models}):
                module = module_from_file("mds01_test_pinned_vsvig", source_path)
            self.assertEqual(source_path.read_text(encoding="utf-8"), original)

        self.assertIs(module.register_model, register_model)
        self.assertTrue(module.loaded)

    def test_nnpack_is_unchanged_by_default_on_x86(self) -> None:
        calls: list[bool] = []
        torch = SimpleNamespace(
            backends=SimpleNamespace(
                nnpack=SimpleNamespace(set_flags=calls.append),
            )
        )

        with patch.dict(os.environ, {}, clear=True), patch("platform.machine", return_value="x86_64"):
            _configure_torch_backend(torch)

        self.assertEqual(calls, [])

    def test_nnpack_is_disabled_by_default_on_arm64(self) -> None:
        calls: list[bool] = []
        torch = SimpleNamespace(
            backends=SimpleNamespace(
                nnpack=SimpleNamespace(set_flags=calls.append),
            )
        )

        with patch.dict(os.environ, {}, clear=True), patch("platform.machine", return_value="aarch64"):
            _configure_torch_backend(torch)

        self.assertEqual(calls, [False])

    def test_nnpack_can_be_enabled_explicitly(self) -> None:
        calls: list[bool] = []
        torch = SimpleNamespace(
            backends=SimpleNamespace(
                nnpack=SimpleNamespace(set_flags=calls.append),
            )
        )

        with patch.dict(
            os.environ, {"MDS01_NNPACK_ENABLED": "true"}, clear=True
        ):
            _configure_torch_backend(torch)

        self.assertEqual(calls, [True])

    def test_invalid_nnpack_setting_fails_closed(self) -> None:
        torch = SimpleNamespace(
            backends=SimpleNamespace(nnpack=SimpleNamespace(set_flags=lambda _value: None))
        )

        with patch.dict(
            os.environ, {"MDS01_NNPACK_ENABLED": "sometimes"}, clear=True
        ), self.assertRaises(DetectionError):
            _configure_torch_backend(torch)


if __name__ == "__main__":
    unittest.main()
