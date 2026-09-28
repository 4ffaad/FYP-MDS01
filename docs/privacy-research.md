# Privacy and model-score research note

MDS01 is a research prototype. It reduces practical exposure of uploaded EEG,
but it does not prove that a person cannot be re-identified and it does not
provide a clinical diagnosis.

## What each protection does

| Layer                          | What it protects                                                                                                                     | What it does not promise                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| AES-256-GCM storage encryption | Files at rest and tamper detection while the backend owns them                                                                       | It does not remove biometric information from decrypted EEG.                     |
| Metadata scrub                 | EDF patient, operator, equipment, sex, birthdate/date and free-text metadata; only the exact reviewed 18-channel montage is retained | It preserves required waveform values, so EEG-derived identity risk remains.     |
| Signal obfuscation             | A keyed, lossy, shape-preserving representation used by both detector and privacy evaluation                                         | It is experimental risk reduction, not formal anonymity or differential privacy. |
| Minimization                   | Deletes the original archive, full temporary files, and non-flagged recording artifacts                                              | It does not make the retained positive context risk-free.                        |
| Research reference labels      | Optional CHB-MIT sidecars and summary intervals stored for offline evaluation                                                        | They remain internal and never decide the dashboard model alert.                 |

The public EEG API exposes generated IDs, safe technical metadata, predictions,
score timelines, and non-clinical explanation JSON. It never exposes reference
annotation labels, original names, patient references, filesystem paths,
cryptographic keys, or artifact contents. A local-only signal endpoint can
return a bounded retained positive clip when explicitly enabled; it is disabled
by default. Video detection separately returns fixed model-provenance hashes so
reviewers can identify the loaded checkpoints; those hashes are not storage
secrets and do not expose media.

The one-patient intake keeps report parsing on the loopback macOS frontend
server and returns a bounded, editable list of labeled fields and unlabelled
report text. It does not infer age from DOB or diagnose/normalize report values.
The operator may keep, edit, unselect, or remove each row; oversized drafts are
marked for review against the source. The source document is not retained. Only
explicitly selected rows are sent after confirmation and stored as AES-GCM
ciphertext under a dedicated subkey derived from `MDS01_STORAGE_KEY`, bound to
case and owner. A selected unlabelled-text row can contain report excerpts, so
the encrypted profile may include any details the operator chooses to keep.
New encrypted payloads use version 3; legacy version-1 and version-2 profiles
remain readable. The dedicated authenticated profile endpoint returns reviewed
fields only to that owner; generic case/session serializers remain
de-identified. Profile review is an account attestation, not verified clinician
authentication.

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

The pinned local H5 research/demo output is surfaced as
`uncalibrated_model_score`, not as a probability. It remains non-diagnostic and
is available only through the explicit local research profile. No clinical
validation is implied by the presence of a hash-pinned artifact.

For model processing, the backend creates a separate scrubbed EDF and never
edits the encrypted source in place. It requires every channel in the reviewed
18-channel montage, writes only those channels in contract order, and discards
extra channel labels; missing or duplicate required channels stop processing.
It blanks patient/operator/free-text fields and annotation descriptions,
neutralizes the source calendar timestamp, and verifies the rewritten EDF
before preprocessing. Relative annotation timing is preserved for review. This
metadata-only operation is not waveform anonymization: EEG itself may retain
person-specific biometric information.

For legacy `.e` recordings with acquisition gaps, processing preserves each
segment boundary and source-relative model-window time. Filters and windows do
not span a gap; per-channel normalization uses observed samples without adding
synthetic gap data. Positive gapped recordings retain only encrypted
model-window artifacts with their timestamps, rather than an EDF clip whose
compressed timeline could be mistaken for continuous acquisition.

## Visual detection privacy boundary

The visual detector is a separate video workflow, not a second EEG input. Its
source is written to owner-scoped encrypted storage before background processing.
Every frame receives full-frame blur regardless of face detection; detector
coverage supplies quality flags, not a selective blur mask. The strict VSViG
workflow still applies its reviewed native-resolution and quality gates.
Separately, `face-redacted-pose-preview` lets the pinned Lightweight OpenPose
detector process only the full-frame-blurred intermediate and draws an optional
body-joint overlay. Low face coverage can keep that stronger full-blur artifact
available for owner review with a `needs_review` status; it does not turn the
preview into a classification result. Preview output is encrypted, case/owner
scoped, audio-free and retained only until job expiry. OpenCV handles decode,
blur and rendering; Lightweight OpenPose is the actual body-keypoint model.
Neither pipeline computes facial Action Units: a reviewed face-AU model and
input contract have not been selected. Audio is excluded from model input.

The local one-patient workflow preflights selected detection candidates through
a temporary encrypted upload that is deleted without inference. VSViG admits
native 1920×1080 originals by default. Its separately configured experimental
letterbox option does not add captured detail or establish equivalence with
native inputs. A privacy/pose preview uses the privacy utility's bounded
dimensions and does not bypass the VSViG contract. Explicit same-patient
association does not establish EEG/video synchronization or a clock offset.

The encrypted source may remain in private storage while the job is queued or
processing. Successful completion removes the source and transient plaintext
work files before publishing the terminal result. Failed/interrupted jobs run
cleanup; if deletion fails, an internal retry record remains until a later
cleanup sweep succeeds. Normal retention is modality-specific: video detection keeps encrypted
predictions/provenance until expiry; its privacy-safe visualization is
transient and deleted after validation, while the separate video-privacy utility keeps its encrypted audio-free
transformed output and preview until expiry. Neither
workflow intentionally retains the original video until expiry.

The keypoint model is Lightweight OpenPose with the `pose.pth` checkpoint
published alongside VSViG. VSViG then consumes fifteen Gaussian `32×32` patches
over thirty sampled frames. Patch-occlusion evidence reports input-region
sensitivity only. It does not identify a seizure cause, establish anatomy as a
mechanism, or prove that redaction preserved clinical performance.

Full-frame blur is a privacy transform, not formal anonymity. Haar detection
can miss faces; low coverage fails the detection job and intermittent coverage
is flagged for review, but blur still covers the entire frame. Privacy
effectiveness still requires representative face-box review, false-negative
analysis and a patient-disjoint raw-versus-redacted evaluation.

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
