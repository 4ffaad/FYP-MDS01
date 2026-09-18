"""Tests for the pinned VSViG bundle metadata and upstream import boundary."""

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend.app.video_detection import contract as contract_module
from backend.app.video_detection.contract import (
    DEFAULT_PREPROCESSING,
    LICENSES,
    POSE_COMMIT,
    POSE_REPOSITORY,
    POSE_SOURCES,
    UPSTREAM_ARTIFACTS,
    UPSTREAM_COMMIT,
    UPSTREAM_REPOSITORY,
    UPSTREAM_SOURCES,
    DetectionError,
    _bundle_layout,
    _strict_file,
    digest,
    load_contract,
)
from backend.app.video_detection.runtime import _track_single_pose, module_from_file
from backend.scripts.install_vsvig_assets import (
    _checked_env_path,
    _download_verified,
    _reject_symlink_components,
)
from backend.scripts.video_contract import template


class VSViGRuntimeTests(unittest.TestCase):
    @staticmethod
    def _synthetic_bundle(root: Path) -> str:
        expected = {**UPSTREAM_SOURCES, **UPSTREAM_ARTIFACTS, **POSE_SOURCES, **LICENSES}
        for name in expected:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"mds01-test-asset")
        contract = {
            "reviewed": True,
            "review_scope": "test",
            "review_reference": "test contract",
            "version": "mds01-vsvig-technical-1",
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "pose_repository": POSE_REPOSITORY,
            "pose_commit": POSE_COMMIT,
            "sha256": {name: digest(root / name) for name in sorted(expected)},
            "threshold": 0.5,
            "preprocessing": deepcopy(DEFAULT_PREPROCESSING),
        }
        contract_path = root / "contract.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        return digest(contract_path)

    @classmethod
    @contextmanager
    def _synthetic_contract(cls, root: Path):
        contract_hash = cls._synthetic_bundle(root)
        with patch.object(
            contract_module,
            "UPSTREAM_SOURCES",
            {name: digest(root / name) for name in UPSTREAM_SOURCES},
        ), patch.object(
            contract_module,
            "UPSTREAM_ARTIFACTS",
            {name: digest(root / name) for name in UPSTREAM_ARTIFACTS},
        ), patch.object(
            contract_module,
            "POSE_SOURCES",
            {name: digest(root / name) for name in POSE_SOURCES},
        ), patch.object(
            contract_module,
            "LICENSES",
            {name: digest(root / name) for name in LICENSES},
        ), patch.object(
            contract_module,
            "REVIEWED_CONTRACT_SHA256",
            contract_hash,
        ), patch.dict(os.environ, {"VSVIG_CONTRACT_SHA256": contract_hash}, clear=False):
            yield

    def test_module_from_file_registers_module_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            module_name = "mds01_test_upstream_module"
            module_path = Path(directory) / "upstream.py"
            module_path.write_text(
                "import sys\n"
                "registered = sys.modules[__name__] is not None\n"
            )
            loaded = module_from_file(module_name, module_path)
            self.addCleanup(sys.modules.pop, module_name, None)
            self.assertTrue(loaded.registered)
            self.assertIs(sys.modules[module_name], loaded)

    def test_contract_template_contains_official_runtime_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = template(Path(directory), reviewed=True)
        preprocessing = contract["preprocessing"]
        self.assertTrue(contract["reviewed"])
        self.assertEqual(contract["upstream_commit"], "1026e7e7f2287b96f3cc375830f2836ffdf4588e")
        self.assertEqual(contract["pose_commit"], "d23c284b09acf27a163e1febd511e7482cac25ed")
        self.assertEqual(preprocessing["frames"], 30)
        self.assertEqual(preprocessing["stride_frames"], 3)
        self.assertEqual(preprocessing["sample_fps"], 6.0)
        self.assertEqual(preprocessing["patch_labels"][0], "nose")
        self.assertEqual(len(preprocessing["patch_labels"]), 15)

    def test_installer_rejects_symlinked_environment_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "real.env"
            target.write_text("APP_ENV=test\n")
            link = root / ".env"
            link.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "regular file"):
                _checked_env_path(link)
            with self.assertRaisesRegex(RuntimeError, "symlinks"):
                _download_verified(link, "https://github.com/example/repo", "revision", "file", digest(target))
            real_parent = root / "real-parent"
            real_parent.mkdir()
            parent_alias = root / "parent-alias"
            parent_alias.symlink_to(real_parent, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlinks"):
                _checked_env_path(parent_alias / ".env")

            real_asset_dir = root / "asset-dir"
            real_asset_dir.mkdir()
            asset_alias = root / "asset-alias"
            asset_alias.symlink_to(real_asset_dir, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlinks"):
                _reject_symlink_components(asset_alias)

    def test_contract_rejects_internal_asset_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                (root / "VSViG-base.pth").unlink()
                (root / "VSViG-base.pth").symlink_to(root / "pose.pth")
                with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                    load_contract(root)

    def test_contract_rejects_symlinked_contract_and_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                contract_path = root / "contract.json"
                contract_path.rename(root / "contract-real.json")
                contract_path.symlink_to(root / "contract-real.json")
                with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                    load_contract(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                (root / "openpose").rename(root / "openpose-real")
                (root / "openpose").symlink_to(root / "openpose-real", target_is_directory=True)
                with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                    load_contract(root)

    def test_contract_rejects_unexpected_root_python_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                (root / "unexpected.py").write_text("# unreviewed\n", encoding="utf-8")
                with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                    load_contract(root)

    def test_contract_rejects_changed_reviewed_preprocessing_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                contract_path = root / "contract.json"
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                contract["preprocessing"]["sample_fps"] = 7.0
                contract_path.write_text(json.dumps(contract), encoding="utf-8")
                with patch.dict(os.environ, {"VSVIG_CONTRACT_SHA256": digest(contract_path)}):
                    with self.assertRaisesRegex(DetectionError, "contract_unreviewed"):
                        load_contract(root)

    def test_contract_requires_the_independent_reviewed_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._synthetic_contract(root):
                with patch.object(contract_module, "REVIEWED_CONTRACT_SHA256", "0" * 64):
                    with self.assertRaisesRegex(DetectionError, "contract_unreviewed"):
                        load_contract(root)

    def test_bundle_layout_rejects_invalid_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            real_directory = parent / "real"
            real_directory.mkdir()
            symlink = parent / "symlink"
            symlink.symlink_to(real_directory, target_is_directory=True)
            regular_file = parent / "regular"
            regular_file.write_text("not a directory", encoding="utf-8")
            fifo = parent / "fifo"
            os.mkfifo(fifo)
            for invalid_root in (symlink, regular_file, fifo):
                with self.subTest(invalid_root=invalid_root.name):
                    with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                        _bundle_layout(invalid_root)

    def test_pose_identity_switch_fails_closed(self):
        class FakePose:
            def __init__(self, keypoints, confidence):
                self.keypoints = keypoints
                self.confidence = confidence
                self.id = None

        assigned_ids = iter((7, 7, 9))

        def track(_previous, current, **_kwargs):
            current[0].id = next(assigned_ids)

        keypoints = __import__("numpy").zeros((18, 3), dtype="float32")
        previous = _track_single_pose([], keypoints, FakePose, track)
        previous = _track_single_pose(previous, keypoints, FakePose, track)
        with self.assertRaisesRegex(DetectionError, "ambiguous_or_missing_pose"):
            _track_single_pose(previous, keypoints, FakePose, track)

    def test_strict_file_rejects_normalized_relative_components(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            (root / "file").write_text("content", encoding="utf-8")
            for relative in ("", "./file", "../file", "nested\\..\\file"):
                with self.subTest(relative=relative):
                    with self.assertRaisesRegex(DetectionError, "asset_mismatch"):
                        _strict_file(root, relative)


if __name__ == "__main__":
    unittest.main()
