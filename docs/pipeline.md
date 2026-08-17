# EEG processing pipeline

## End-to-end flow

```text
ZIP upload
   |
   v
Create session + register BackgroundTask
   |
   v
Validate archive and EDFs
   |
   v
Extract EDF files
   |
   v
De-identify EDF metadata
   |
   v
Preprocess signal
   |
   v
Create model windows
   |
   v
Run inference adapter
   |
   v
Write explanation artifacts
   |
   v
Store status and results
```

## Validation

The storage and validation services reject invalid ZIP files, unsafe archive
paths, oversized members, duplicate EDF basenames, missing EDF files, unreadable
EDF files, mixed channel sampling rates, and unusable signal data.

One invalid recording is marked failed without stopping sibling recordings.

## De-identification

The original EDF is never modified in place. A new EDF is written with:

- generated `REC-*` patient name/code;
- blank personal and administrative fields;
- a neutral calendar start date;
- technical signal headers preserved;
- relative annotation timing preserved.

The exact privacy policy must be reviewed before clinical use.

## Preprocessing contract

The current project contract is:

```text
sampling rate: 256 Hz
channels: exact configured 18 bipolar channels
window: 4 seconds
samples per window: 1024
model input: (N, 1024, 18), float32
```

The signal pipeline applies band-pass filtering, notch filtering, per-channel
z-score normalization, and artifact clipping before window creation.

## Inference and explanations

The configured runtime is currently `development-stub`, version `stub-0.1.0`.
The repository also contains an unintegrated model artifact at
`backend/model/best_seizure_model.h5`; it is intentionally not loaded because
its framework, input contract, and training-time preprocessing still require
verification. The active stub produces deterministic placeholder probabilities
based on opaque IDs. These outputs are not clinical predictions.

Explanation artifacts are JSON files labelled `is_clinical: false`. They are
placeholders until the actual model and evaluated explanation method are
supplied.
