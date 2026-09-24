# Presentation readiness

This checklist describes what MDS01 can demonstrate now and what is still
needed before presenting it as a validated clinical system. It is not a claim
of accuracy, anonymity or regulatory compliance.

## The product story

MDS01 has exactly two input modalities:

1. One EEG ZIP archive containing EDF/EDF+, legacy Nicolet `.e`, or supported Nicolet `.data` files with matching `.head` sidecars.
2. One separate video file.

A paired submission uses one shared analysis workspace, but the backend keeps
EEG and video processing independent. Do not describe the EEG ZIP as containing
video.

Legacy Nicolet `.e` recordings are parsed through the bounded reader, converted
to a scrubbed EDF, and sent through the same reviewed EEG contract. Embedded
event timing is retained only as sanitized timing/kind metadata for human
review; raw annotation text and `.doc` reports are not imported automatically.
AVI is accepted as a video source and is decoded into the existing audio-free,
privacy-safe video path.

The video review story is:

```text
video upload
  → encrypt source
  → face detection plus full-frame blur on every frame
  → shared protected input for Lightweight OpenPose keypoints and VSViG patches
  → VSViG scoring and evidence timeline
```

Audio is excluded from the visual model input. The uploaded source may contain
audio while it is encrypted and waiting for processing; the visual runtime does
not decode audio into model input. The original and temporary model-input video
are deleted after the job; only encrypted scores/provenance and the
owner-scoped, audio-free privacy-safe visualization are retained until expiry.
The separate Video privacy utility has a different owner-only output policy and
is not the seizure detector.

## What is implemented

- Authenticated owner-scoped EEG and video job APIs.
- Development-only local administrator role, with a password generated into the
  ignored `.env` rather than embedded in docs or source.
- Encrypted application storage after multipart intake; framework upload spool
  data remains private to the backend container and is cleaned with the job.
- Every frame receives full-frame blur; Haar face-detection coverage informs
  quality flags and the minimum-coverage gate.
- A fail-closed rule when face coverage is too low.
- The published VSViG base architecture and checkpoint.
- The published `pose.pth` checkpoint with the pinned Lightweight OpenPose
  implementation used to extract `(x, y, confidence)` keypoints.
- The published dynamic partition tensor.
- Hash-checked, read-only external model mounts.
- Startup verification that loads both checkpoints and performs a tensor-only
  forward pass.
- Per-window uncalibrated model scores, merged flagged intervals and bounded
  patch-occlusion sensitivity evidence.
- Encrypted prediction-result retention plus an owner-scoped encrypted,
  full-frame-blurred, audio-free review visualization; no source
  playback endpoint.
- Synchronized protected playback, score timeline and event navigation.
- Research-only labels throughout the UI.
- A combined review report with sanitized EEG event times, separate EEG/video
  model evidence, model provenance, and explicit non-clinical caveats.
- A local-only demo offset control. A selected pair and its offset remain
  visibly assumed, are not persisted, and are not represented as verified
  synchronization.
- Browser Print / Save as PDF for the visible report; no report is uploaded or
  retained by the backend.

## Current local demo constraints

- The default Compose EEG runtime is `development-stub`; its scores demonstrate
  UI/data flow only. It does not provide real EEG model predictions or SHAP
  attribution for this dataset.
- A read-only inventory found 552 640×480 AVI files and 806 1920×1080 MP4
  files. Inventory metadata is not full decode or model-admission evidence.
  Low-resolution letterboxing remains disabled by default.
- An isolated full-frame-blur-to-VSViG smoke on four small native-resolution
  MP4 candidates had three privacy-admission rejections; the one that passed
  privacy was rejected by the ambiguous/missing-pose gate. No successful video
  prediction has been verified. Do not present a privacy- or pose-rejected clip
  as a model result.
- No authoritative EEG/video match or clock offset is established. The report's
  default 0-second offset is an explicitly labeled demo assumption, not a
  measured synchronization value.
- Source EEG event markers are shown without raw annotation text. They are not
  model outputs, ground truth, or diagnoses, and they require human review.

## What is still missing for a credible presentation

### Required to run the real video demo

- [ ] Docker Desktop is running and can build the `linux/amd64` backend image.
- [ ] The pinned asset initializer has populated the server-side named Docker
      volume and completed successfully outside the Git checkout.
- [ ] `VSVIG_CONTRACT_SHA256` is present in the ignored `.env`; `VSVIG_ASSET_DIR`
      remains the internal container path `/opt/vsvig`, not a user setting.
- [ ] If operator inventory/inspection is part of the demo, an approved server
      directory is mounted read-only for that diagnostic command only.
- [ ] The startup verification command passes before the demo.
- [ ] A non-patient or consented video is available at 1920×1080, constant frame
      rate, one visible person, and at least five seconds long.
- [ ] The clip has enough lighting and framing for face detection and complete
      pose extraction.
- [ ] The demo account is configured locally; its password is read privately
      from `.env` and never placed in slides, screenshots or chat.

### Required to claim model performance

- [ ] Written provenance for the video data, checkpoint, pose model and every
      preprocessing parameter.
- [ ] Permission to use the video data, with a documented retention and access
      policy.
- [ ] Clinician-reviewed seizure onset and offset annotations, including the
      time basis and clock synchronization.
- [ ] Patient-disjoint train, validation/calibration and test splits.
- [ ] A negative set that represents the intended camera, bedding, lighting,
      staff movement and non-seizure activity.
- [ ] A declared unit of evaluation: frame, window, event or recording.
- [ ] Sensitivity/recall, specificity, precision, F1, ROC-AUC and
      precision-recall results where appropriate.
- [ ] False alarms per hour and event-level sensitivity.
- [ ] Detection latency relative to the reviewed visible-event onset.
- [ ] Confidence intervals or an explicitly justified uncertainty method.
- [ ] Threshold selection on validation data only; the test set remains unseen.
- [ ] Calibration evaluation before using probability or confidence language.
- [ ] A documented comparison of raw video versus full-frame-blurred video, with
      patient-disjoint evaluation and score drift.
- [ ] A documented policy for face-detector misses, multiple people, staff
      entering the frame, occlusion and no-pose clips.
- [ ] A measured CPU latency, memory footprint and maximum safe concurrent job
      count on the intended demo hardware.
- [ ] A decision on whether the app should implement the VSViG paper's temporal
      accumulation rule. The current app uses a per-window research threshold;
      it must not be presented as the paper's final event detector.

### Required to claim privacy protection

- [ ] Face-detection coverage measured on representative clips, not just a
      successful application response.
- [ ] False-negative review for frontal, profile, masked, low-light and
      partially occluded faces.
- [ ] A human review of whether always-on full-frame blur preserves enough pose
      signal for the intended use.
- [ ] Verification that no source or temporary model-input video is returned by
      the detection API, while the approved visualization endpoint remains
      authenticated, owner-scoped, audio-free and expiry-cleaned.
- [ ] Verification of cleanup after success, failure, expiry and server restart.
- [ ] A threat model for decrypted work files, logs, backups, Docker mounts and
      local administrator access.
- [ ] Production authentication, HTTPS, rate limits, secret management and a
      durable worker before network deployment.
- [ ] Legal/ethics review of biometric video processing and the chosen model
      licenses.

## Recommended slide order

1. **Problem and review context** — why visual seizure review needs a temporal
   signal and human review; state the research-only boundary.
2. **Two inputs, one workspace** — one EEG EDF ZIP plus one separate video; show
   that the modalities remain independent.
3. **Privacy-first video path** — encryption, full-frame blur on every frame,
   detector coverage/quality gate, no audio model input, transient cleanup.
4. **Model stack** — Lightweight OpenPose supplies keypoints; official VSViG
   consumes 15 Gaussian 32×32 patches over 30 sampled frames; the dynamic
   partition tensor is an input asset, not a second classifier.
5. **Evidence timeline** — show window scores, threshold, flagged intervals and
   patch-occlusion sensitivity; label it uncalibrated and non-clinical.
6. **System and ownership boundary** — authenticated API, encrypted private
   storage, owner filtering, background processing and retention.
7. **Validation plan** — patient-disjoint labels, metrics, calibration, privacy
   coverage and latency; show measured results only when they exist.
8. **Limitations and next work** — no diagnosis, no anonymity guarantee, no
   recording-level confidence, single-person pose ceiling, and the remaining
   evaluation/deployment gates.

## Five-minute live demo

1. Start Docker and run the asset verification command from
   [the video runbook](video-detection.md).
2. Open the frontend and sign in with the locally configured development
   account.
3. Open **New analysis** and show that the EEG archive and video are separate
   upload lanes.
4. Submit the consented EEG and video, then open the combined review report.
5. Select the intended completed EEG recording if the archive contains more
   than one. Review the sanitized source event times separately from model
   outputs.
6. If demonstrating a pairing, state that it is assumed. The default offset is
   0 seconds; change it only to a supplied demo value and point out that it is
   local to the page and not verified or saved.
7. Show EEG window scores and, only when present, its model-specific SHAP
   sensitivity artifact. State that the current stub has no EEG attribution.
8. Show video quality/provenance, uncalibrated scores and patch-occlusion
   sensitivity only if the video job actually reached inference. If a clip is
   rejected by timing, resolution or pose gates, show that fail-closed status;
   do not imply a prediction exists.
9. Use **Print / Save as PDF** to create a local report copy; confirm the PDF
   retains the assumed-pairing and research-only labels.
10. End with the validation gaps rather than implying that a runnable demo is a
    clinically validated detector. Never manufacture a positive example.

## Acceptance gate before changing the wording

Use these labels until the corresponding evidence exists:

- "research prototype"
- "uncalibrated model score"
- "flagged interval for human review"
- "full-frame-blurred model input"
- "privacy transform; anonymity not guaranteed"

Reserve these labels for a later reviewed release:

- "probability" or "confidence"
- "validated seizure detector"
- "anonymous video"
- "clinical explanation"
- "real-time"
- "safe for clinical use"
