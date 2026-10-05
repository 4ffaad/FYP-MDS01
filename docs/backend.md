# Backend guide

This is the backend's practical map for changing or tracing a request. For a
plain-language model walkthrough, start with
[EEG and video inference](inference-walkthrough.md). API schemas are available
from the running app at http://127.0.0.1:8000/docs.

## How a request is handled

FastAPI routes parse and validate HTTP input. Services own workflows.
Repositories own database queries. Long EEG jobs run through FastAPI
BackgroundTasks after the request returns.

The main EEG path is:

```text
upload → encrypted draft → session → validate → de-identify → preprocess
       → H5 or development stub → save per-window scores → clean temporary files
```

Malformed recordings fail independently. A failed job means no supported score
was produced; it is not a negative seizure result.

## EEG files and model input

Supported inputs are EDF/EDF+, the supported legacy Nicolet .e layout, and
Nicolet .data with its matching .head sidecar.

The legacy .e adapter accepts the reviewed 33-channel, referential, 500 Hz
delivery layout. It maps the reviewed electrode names to the configured
montage, derives the required 18 bipolar channels, and resamples to 256 Hz.
It then writes a separate scrubbed EDF for the common processing path; it
doesn't rewrite the original .e file. Different layouts or ambiguous channels
fail closed. For .e recordings with acquisition gaps, filtering and windows
stay within each observed segment and preserve elapsed offsets.

The model-input contract is:

- 256 samples per second;
- the exact configured 18 bipolar channels, in contract order;
- four-second windows with a two-second stride;
- float32, shape (N, 1024, 18).

Identifying EDF metadata is removed from the derived model input. Relative
event timing may be retained in sanitized form for human review; raw annotation
text is not returned by the public API. Scrubbing metadata does not anonymize
the EEG waveform.

The configured review policy retains the complete waveform as an encrypted
artifact after successful inference, even when no model window is flagged.
For legacy `.e` files, the viewer uses the reviewed 18-channel bipolar montage
and, when present at the common source rate, the five EOG/ECG/chin-difference/
photic traces. The uploaded `.e` and transient plaintext are removed during
session cleanup. Signal reads remain bounded by time range and owner-scoped.

## Model runtimes and result meaning

- **Development stub:** deterministic synthetic scores for workflow testing;
  it is not seizure inference.
- **H5:** local Keras artifact and reviewed contract are mounted read-only.
  Startup validates the artifact hash and input/output contract and fails
  closed if either is missing or mismatched.
- **Current output:** research score per EEG window. The supplied local
  contract is uncalibrated; do not describe its score as a probability,
  confidence, accuracy, or recording-level risk. SHAP is optional and appears
  only when enabled with its approved background data.

The H5 model, contract, and SHAP backgrounds are local-only assets. Do not put
them in Git or the Docker image. See [setup](setup.md) for the runtime choice.

## Storage, ownership, and cleanup

PostgreSQL stores accounts, job/session state, safe metadata, and predictions.
Encrypted EEG/video bytes remain in private filesystem-backed storage. Do not
store patient binaries in PostgreSQL or expose private paths in API responses.
Patient profiles are encrypted and owner-scoped. The patient-folder intake
extracts report text locally and does not retain the source document.

Protected routes filter records by owner. The API does not return original
filenames, patient references, cryptographic keys, or raw source files.
Temporary source and processing files are cleaned up after completion; only
artifacts allowed by the configured retention policy remain encrypted.

New EEG and video file envelopes bind AES-GCM authentication to their
storage-relative session, job, and artifact path. Draft promotion re-encrypts
for the final session path. Legacy envelopes remain readable and are atomically
rewrapped after successful materialization when possible. Until every existing
legacy file has been read or explicitly migrated, keep write access to the
private storage volume trusted. Patient profile and source-report encryption
also bind ciphertext to the owner and case.

Signal preview is disabled by default and is limited to policy-approved
retained EEG. Never log patient-identifying values or raw upload contents.
For metadata-scrubbed legacy `.e` recordings, the encrypted positive-signal
artifact may also include EOG right/left, ECG, chin 1–chin 2, and photic review
traces over the same bounded source-time ranges. These traces share the EEG
artifact's owner checks, expiry, and deletion; signal-obfuscation profiles omit
them. They are visual review channels and are not model inputs.

## Routes and code locations

Use Swagger for the current complete route schemas. Main route groups:

- /api/auth/ — registration, login, session, logout;
- /api/uploads/ and /api/sessions/ — drafts, EEG sessions, status, deletion;
- /api/recordings/ — predictions, sanitized annotations, explanations, signal;
- /api/cases/ — owner-scoped cases and reviewed profiles;
- /api/video-detection/ — separate VSViG jobs and review playback;
- /api/video-privacy/ — separate protected-video transform.

`DELETE /api/cases/{case_id}` removes the owner's linked EEG and video jobs,
encrypted retained media, patient profile, and source report. It returns `409`
while any linked processing job is active.

`GET /api/cases` includes safe workload totals for EEG recordings and video
clips, flagged EEG windows, processing state, and results readiness. Patient
names and short report conclusions appear only from reviewed, owner-scoped
profiles; original filenames and source metadata stay private.

| Start here | Responsibility |
| --- | --- |
| backend/app/main.py | FastAPI setup, routers, startup checks and cleanup |
| backend/app/api/ | HTTP parsing and safe responses |
| backend/app/services/ | Upload, processing, storage, auth and cleanup workflows |
| backend/app/eeg/, backend/app/ml/, backend/app/privacy/ | EEG reading, tensor creation, privacy and inference |
| backend/app/video_detection/ | VSViG/pose runtime and video contract |
| backend/app/database/ | Models, engine, session helper and repositories |
| backend/migrations/versions/ | Alembic schema history |

Use a new Alembic migration for schema changes. Do not rely on create_all()
for runtime schema management.
