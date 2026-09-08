"""Research evaluation and explainability boundary tests."""

from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from backend.app.ml.interface import WindowPrediction
from backend.app.ml.shap_explanation import ShapExplanationError, _normalise_attributions, build_shap_explanations
from backend.app.privacy.methods import CANONICAL_COMBINED, METADATA_SCRUB
from backend.app.research.evaluation import EvaluationRecording
from backend.app.research.evaluation import _safe_reason, build_metrics_report, split_subjects
from backend.app.research.calibration import fit_temperature, temperature_scale
from backend.app.services.processing_service import _shap_background_for_profile
from backend.scripts.create_shap_background import (
    _choose_background,
    _collect_candidates,
    _select_non_seizure_windows,
    create_backgrounds,
)


class EvaluationAndExplanationTests(unittest.TestCase):
    """Verify labelled evaluation and bounded research attribution behavior."""

    def test_fixed_manifest_is_patient_disjoint(self) -> None:
        manifest = split_subjects()
        self.assertEqual(manifest["train"], ("chb01", "chb02", "chb03", "chb04", "chb05", "chb06"))
        self.assertEqual(manifest["calibration"], ("chb07", "chb08"))
        self.assertEqual(manifest["test"], ("chb09", "chb10"))
        self.assertTrue(set(manifest["train"]).isdisjoint(manifest["calibration"]))
        self.assertTrue(set(manifest["calibration"]).isdisjoint(manifest["test"]))

    def test_metrics_report_contains_accuracy_and_calibration_without_window_split(self) -> None:
        report = build_metrics_report(
            labels=[0, 0, 1, 1],
            scores=[0.1, 0.8, 0.6, 0.9],
            patient_ids=["chb09", "chb09", "chb10", "chb10"],
            duration_hours=1.0,
            threshold=0.5,
            seed=7,
        )
        self.assertEqual(report["classification"]["confusion_matrix"], [[1, 1], [0, 2]])
        self.assertAlmostEqual(float(report["classification"]["accuracy"]), 0.75)
        self.assertIn("roc_auc", report)
        self.assertIn("average_precision", report)
        self.assertIn("patient_bootstrap_f1", report)
        self.assertEqual(report["patient_bootstrap_f1"]["seed"], 7)
        self.assertIn("negative_log_likelihood", report["calibration"])

    def test_temperature_scaling_is_positive_and_profile_ready(self) -> None:
        labels = [0, 0, 0, 1, 1, 1]
        scores = [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]
        temperature = fit_temperature(labels, scores)
        calibrated = temperature_scale(scores, temperature)
        self.assertGreater(temperature, 0)
        self.assertEqual(calibrated.shape, (6,))
        self.assertTrue(np.isfinite(calibrated).all())
        self.assertTrue(np.all((calibrated >= 0) & (calibrated <= 1)))

    def test_h5_calibration_requires_both_active_privacy_profiles(self) -> None:
        from backend.app.ml.h5_inference import H5InferenceService, H5ModelError

        service = H5InferenceService.__new__(H5InferenceService)
        service.score_type = "calibrated_probability"
        service.calibration_method = "temperature_scaling"
        service.calibration_profiles = {
            METADATA_SCRUB: {
                "status": "active",
                "method": "temperature_scaling",
                "temperature": 1.0,
                "version": "v1",
                "dataset": "CHB-MIT",
                "subjects": ["chb07", "chb08"],
                "metrics": {"brier_score": 0.1, "expected_calibration_error": 0.1, "negative_log_likelihood": 0.2},
            }
        }
        with self.assertRaisesRegex(H5ModelError, "metadata-scrub\\+signal-obfuscation"):
            service._validate_calibration_profiles()

    def test_h5_calibration_selects_the_active_privacy_profile(self) -> None:
        from backend.app.ml.h5_inference import H5InferenceService

        service = H5InferenceService.__new__(H5InferenceService)
        service.model = MagicMock()
        service.model.predict.return_value = np.asarray([[0.2]], dtype=np.float32)
        service.threshold = 0.5
        service.score_type = "calibrated_probability"
        service.calibration_method = "temperature_scaling"
        profile = lambda temperature, version: {
            "status": "active",
            "method": "temperature_scaling",
            "temperature": temperature,
            "version": version,
            "dataset": "CHB-MIT",
            "subjects": ["chb07", "chb08"],
            "metrics": {"brier_score": 0.1, "expected_calibration_error": 0.1, "negative_log_likelihood": 0.2},
        }
        service.calibration_profiles = {
            METADATA_SCRUB: profile(1.0, "baseline-v1"),
            CANONICAL_COMBINED: profile(2.0, "obfuscated-v1"),
        }
        starts = np.asarray([0.0], dtype=np.float32)
        windows = np.zeros((1, 1024, 18), dtype=np.float32)
        baseline = service.predict(windows, starts, "REC-CAL", privacy_method=METADATA_SCRUB)[0]
        obfuscated = service.predict(windows, starts, "REC-CAL", privacy_method=CANONICAL_COMBINED)[0]
        self.assertNotEqual(baseline.probability, obfuscated.probability)
        self.assertEqual(baseline.calibration_version, "baseline-v1")
        self.assertEqual(obfuscated.calibration_version, "obfuscated-v1")

    def test_shap_explanation_is_bounded_and_contains_no_signal_samples(self) -> None:
        class FakeGradientExplainer:
            def __init__(self, model, background):
                self.model = model
                self.background = background

            def shap_values(self, windows):
                return np.ones_like(windows, dtype=np.float32)

        fake_shap = types.SimpleNamespace(GradientExplainer=FakeGradientExplainer)
        windows = np.zeros((2, 1024, 18), dtype=np.float32)
        predictions = [
            WindowPrediction(0, 0.0, 4.0, 0.9, True, score_type="uncalibrated_probability"),
            WindowPrediction(1, 2.0, 6.0, 0.2, False, score_type="uncalibrated_probability"),
        ]
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"shap": fake_shap}):
            background_path = Path(directory) / "background.npy"
            np.save(background_path, np.zeros((2, 1024, 18), dtype=np.float32))
            result = build_shap_explanations(
                model=object(),
                windows=windows,
                predictions=predictions,
                background_path=background_path,
                threshold=0.5,
                max_windows=3,
                time_bins=8,
            )

        self.assertEqual(list(result), [0])
        payload = result[0]
        self.assertEqual(payload["method"], "shap-gradient")
        self.assertEqual(len(payload["channel_scores"]), 18)
        self.assertEqual(len(payload["time_bins"]), 8)
        self.assertNotIn("samples", str(payload))
        self.assertNotIn("path", str(payload))
        self.assertFalse(payload["is_clinical"])

    def test_shap_fails_closed_when_background_is_missing(self) -> None:
        predictions = [WindowPrediction(0, 0.0, 4.0, 0.9, True)]
        with self.assertRaises(ShapExplanationError):
            build_shap_explanations(
                model=object(),
                windows=np.zeros((1, 1024, 18), dtype=np.float32),
                predictions=predictions,
                background_path=Path("missing-shap-background.npy"),
                threshold=0.5,
            )

    def test_shap_normalizes_current_single_output_tensor_shape(self) -> None:
        values = np.zeros((1, 1024, 18, 1), dtype=np.float64)
        normalized = _normalise_attributions(values, 1)
        self.assertEqual(normalized.shape, (1, 1024, 18))
        self.assertEqual(normalized.dtype, np.float32)

    def test_evaluation_exclusions_never_echo_local_paths(self) -> None:
        reason = _safe_reason(ValueError("/private/chbmit/chb09/chb09_01.edf is incompatible"))
        self.assertEqual(reason, "recording is incompatible with the model contract or labels")
        self.assertNotIn("chb09_01", reason)

    def test_background_selection_excludes_reference_seizure_windows(self) -> None:
        windows = np.arange(3 * 1024 * 18, dtype=np.float32).reshape(3, 1024, 18)
        starts = np.array([0.0, 2.0, 4.0], dtype=np.float32)
        selected = _select_non_seizure_windows(windows, starts, [(3.0, 5.0)])
        self.assertEqual(selected.shape, (2, 1024, 18))
        np.testing.assert_array_equal(selected[0], windows[0])
        np.testing.assert_array_equal(selected[1], windows[2])

    def test_background_collection_uses_only_calibration_subjects(self) -> None:
        recordings = [
            EvaluationRecording(Path("chb06.edf"), "chb06", ()),
            EvaluationRecording(Path("chb07.edf"), "chb07", ()),
            EvaluationRecording(Path("chb08.edf"), "chb08", ()),
            EvaluationRecording(Path("chb09.edf"), "chb09", ()),
        ]
        windows = np.zeros((1, 1024, 18), dtype=np.float32)
        with (
            patch(
                "backend.scripts.create_shap_background.discover_chb_mit",
                return_value=(recordings, []),
            ),
            patch("backend.scripts.create_shap_background.deidentify_edf"),
            patch(
                "backend.scripts.create_shap_background.preprocess_edf",
                return_value=(windows, np.array([0.0], dtype=np.float32), {}),
            ) as preprocess,
        ):
            candidates, exclusions = _collect_candidates(Path("/unused"))

        self.assertEqual(preprocess.call_count, 2)
        self.assertEqual(exclusions, 0)
        self.assertEqual(candidates.shape, (2, 1024, 18))

    def test_background_generation_is_deterministic_and_profile_specific(self) -> None:
        candidates = np.arange(64 * 1024 * 18, dtype=np.float32).reshape(64, 1024, 18) / 1000
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.scripts.create_shap_background._collect_candidates",
            return_value=(candidates, 0),
        ), patch(
            "backend.scripts.create_shap_background.read_base64_key",
            return_value=b"k" * 32,
        ):
            summary = create_backgrounds(Path("/unused"), Path(directory))
            metadata = np.load(Path(directory) / "shap-background-metadata.npy")
            obfuscated = np.load(Path(directory) / "shap-background-obfuscated.npy")

        self.assertEqual(summary, {"candidate_windows": 64, "skipped_recordings": 0})
        self.assertEqual(metadata.shape, (32, 1024, 18))
        self.assertEqual(obfuscated.shape, (32, 1024, 18))
        self.assertEqual(metadata.dtype, np.float32)
        self.assertEqual(obfuscated.dtype, np.float32)
        self.assertFalse(np.array_equal(metadata, obfuscated))

    def test_shap_background_path_matches_privacy_profile(self) -> None:
        metadata_path = _shap_background_for_profile(METADATA_SCRUB)
        obfuscated_path = _shap_background_for_profile(CANONICAL_COMBINED)
        self.assertNotEqual(metadata_path, obfuscated_path)
        self.assertIn("metadata", metadata_path.name)
        self.assertIn("obfuscated", obfuscated_path.name)
