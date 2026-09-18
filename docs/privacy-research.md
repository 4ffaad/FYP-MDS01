# Privacy and model-score research note

MDS01 is a research prototype. It reduces practical exposure of uploaded EEG,
but it does not prove that a person cannot be re-identified and it does not
provide a clinical diagnosis.

## What each protection does

| Layer | What it protects | What it does not promise |
| --- | --- | --- |
| AES-256-GCM storage encryption | Files at rest and tamper detection while the backend owns them | It does not remove biometric information from decrypted EEG. |
| Metadata scrub | EDF patient, operator, equipment, date, and free-text metadata | It preserves waveform values, so EEG-derived identity risk remains. |
| Signal obfuscation | A keyed, lossy, shape-preserving representation used by both detector and privacy evaluation | It is experimental risk reduction, not formal anonymity or differential privacy. |
| Minimization | Deletes the original archive, full temporary files, and non-flagged recording artifacts | It does not make the retained positive context risk-free. |
| Research reference labels | Optional CHB-MIT sidecars and summary intervals stored for offline evaluation | They remain internal and never decide the dashboard model alert. |

The public EEG API exposes generated IDs, safe technical metadata, predictions,
score timelines, and non-clinical explanation JSON. It never exposes reference
annotation labels, original names, patient references, filesystem paths,
cryptographic keys, or artifact contents. A local-only signal endpoint can
return a bounded retained positive clip when explicitly enabled; it is disabled
by default. Video detection separately returns fixed model-provenance hashes so
reviewers can identify the loaded checkpoints; those hashes are not storage
secrets and do not expose media.

## EEG detection and retention rule

The model scores every preprocessed window. A recording is model-positive when
at least one window crosses the reviewed threshold. Positive windows are
expanded by up to 10 minutes before each positive window, merged, clipped to the
recording, and retained only as a private encrypted artifact. A dataset `.edf.seizures`
sidecar is a reference label for research reports; it cannot create or remove
a dashboard alert.

The development stub emits deterministic hash-derived values. Those values are
not calibrated probabilities, confidence, accuracy, or evidence of clinical
reasoning. The UI therefore calls them `Development score` and shows the peak
window score, flagged-window count, threshold, and score timeline.

## Visual detection privacy boundary

The visual detector is a separate video workflow, not a second EEG input. Its
source enters through multipart parsing and is then written to owner-scoped
encrypted private storage before background processing. Face redaction runs
before one shared pose/keypoint pass, and that pass fans out to the VSViG
representation and a privacy-safe visualization. The visualization masks the
pose region, draws the same keypoints, contains no audio, and is retained only
as an encrypted owner-scoped artifact until job expiry. The visual model
receives the face-redacted frames and pose-derived patches; it does not consume
the blurred visualization. Audio is excluded from model input.

The keypoint model is Lightweight OpenPose with the `pose.pth` checkpoint
published alongside VSViG. VSViG then consumes fifteen Gaussian `32×32` patches
over thirty sampled frames. Patch-occlusion evidence reports input-region
sensitivity only. It does not identify a seizure cause, establish anatomy as a
mechanism, or prove that redaction preserved clinical performance.

Face redaction is a privacy transform, not formal anonymity. Haar detector
misses trigger full-frame blur and coverage flags; low coverage fails the
detection job. Privacy effectiveness still requires representative face-box
review, false-negative analysis and a patient-disjoint raw-versus-redacted
evaluation.

## Real-model evaluation gate

Before a real model is enabled, its reviewed contract must document its input
shape, training-time preprocessing, output semantics, threshold, model version,
and calibration status. Calibration must use a patient-disjoint validation set;
the test set must remain untouched. Temperature scaling is implemented as a
reviewed contract option and returns `raw_score` plus
`calibrated_probability`. The latter is shown as a probability only after the
calibration procedure has been validated.

The offline research report should include:

- confusion matrix, ROC/AUC, precision-recall/average precision;
- sensitivity, specificity, precision, recall, F1, and false alarms per hour;
- threshold sweep and patient-level bootstrap intervals;
- reliability bins, Expected Calibration Error, and Brier score;
- training accuracy/loss only when a real training-history artifact exists.

Run the evaluator from the repository root with the research dependencies
installed:

```bash
PYTHONPATH=. .venv/bin/python backend/scripts/evaluate_chb_mit.py /path/to/chbmit \
  --privacy-method metadata-scrub \
  --split test \
  --output reports/chbmit.json \
  --plots reports/chbmit.png
```

Repeat with `metadata-scrub+signal-obfuscation` for the optional profile. The
report is the only place where accuracy is appropriate: an arbitrary upload
does not provide ground truth. SHAP is separately gated by
`ENABLE_SHAP_EXPLANATIONS=true` and the two profile-specific backgrounds
generated by `backend/scripts/create_shap_background.py`; its aggregate
attribution is research evidence, not a clinical explanation.

Windows must be split by recording and evaluated with patient-level separation.
Randomly splitting adjacent windows would leak highly correlated information.

## References

- [NIST SP 800-38D: GCM and GMAC](https://csrc.nist.gov/pubs/sp/800/38/d/final)
- [HHS de-identification guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html)
- [EEG as a biometric / brainprint research](https://pmc.ncbi.nlm.nih.gov/articles/PMC9553892/)
- [Guo et al., On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)
