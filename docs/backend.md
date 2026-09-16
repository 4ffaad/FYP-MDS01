# Backend internals

Use this after [setup](setup.md) and [architecture](architecture.md). It is the
implementation reference for API, persistence, processing and EEG research
tools. Video-detection runtime setup lives in [video-detection.md](video-detection.md).

The backend is a FastAPI application backed by SQLite in native prototype mode
or PostgreSQL in Docker/team mode, plus private session-scoped storage. Routes
receive requests; services own the workflow; repositories own database queries.

```mermaid
flowchart TD
    Main[app/main.py] --> Routes[app/api/]
    Routes --> Auth[api/auth.py]
    Auth --> AuthService[services/auth_service.py]
    AuthService --> AuthModels[database/models/auth.py]
    AuthService --> AuthDB[(users and auth_sessions)]
    Routes --> SessionService[services/session_service.py]
    Routes --> Repository[database/repository.py]
    Routes --> Processing[services/processing_service.py]
    Processing --> Validation[services/validation_service.py]
    Processing --> Storage[services/storage_service.py]
    Processing --> Privacy[privacy/]
    Processing --> EEG[eeg/]
    Processing --> ML[ml/]
    Repository --> Models[database/models/eeg.py]
    Migrations[migrations/versions/] --> Models
    Processing --> Database[(SQLite native / PostgreSQL Docker results)]
    Storage --> Files[(Temporary private EEG files)]
```

## Authentication and ownership

The local account API is:

```text
GET  /api/auth/session
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
```

`local-accounts` uses email/password accounts with 8-character minimum
passwords, salted `hashlib.scrypt` records and eight-hour opaque sessions. In
development, it seeds the demo administrator `admin@mds01.local` with password
`12345678`; this account is disabled outside development and is for local demos
only. The
raw session token is sent only as an HttpOnly, SameSite=Lax cookie; PostgreSQL
stores its SHA-256 hash. `require_api_auth` resolves the current user before
protected routes run. EEG sessions, upload drafts and video jobs are filtered
by `owner_user_id`; recordings inherit ownership through their session. A
missing or foreign identifier returns `404`.

Use `AUTH_MODE=local` only for isolated tests. It intentionally bypasses login
and exposes legacy owner-null rows, so it is not a demo or deployment mode.
Production still requires `AUTH_MODE=cloudflare`. Cloudflare Access validates
the JWT issuer, audience and signing key before mapping its subject to a local
ownership row; see [Cloudflare's JWT validation guidance](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/).

## Request and processing flow

```mermaid
flowchart TD
    Upload[POST /api/uploads/drafts] --> Encrypt[Encrypt ZIP with AES-GCM]
    Encrypt --> Draft[Return 201 draft_id and expiry]
    Draft --> Select[Select privacy method]
    Select --> Finalize[POST /api/uploads/drafts/{id}/finalize]
    Finalize --> Queue[Create session, return 202, schedule BackgroundTasks]
    Queue --> Validate[Validate archive and EDF files]
    Validate --> RecordLoop{Each recording independently}
    RecordLoop --> Scrub[Blank identifying EDF fields\nand annotation descriptions]
    Scrub --> Preprocess[Bandpass, notch, normalize, clip]
    Preprocess --> Windows[(N, 1024, 18) float32<br/>4s windows / 2s step]
    Windows --> Method{Privacy method}
    Method --> Control[metadata-scrub\nRequired baseline\nPreserve waveform values]
    Method --> Transform[metadata-scrub + signal-obfuscation\nOptional keyed lossy projection]
    Control --> Detector[Inference adapter]
    Transform --> Detector
    Control --> PSD[PSD features for research evaluation]
    Transform --> PSD
    Detector --> Prediction[Prediction rows]
    Prediction --> Explanation[Non-clinical explanation JSON]
    Prediction --> Retain{Any model-positive windows?}
    Retain -->|yes| Clip[Expand up to 10 minutes, merge, encrypt clip]
    Retain -->|no| Delete[Delete recording temporary files]
    Clip --> SafeResults[Public result endpoints]
    Delete --> SafeResults
    RecordLoop -->|Malformed EDF| Failed[Mark one recording failed]
    Failed --> SafeResults
    SafeResults --> Cleanup[Delete full transient files and archive]
    Legacy[POST /api/sessions/upload] -. compatibility .-> Queue
```

The projection method is intentionally shape-preserving so the same transformed
windows feed both downstream branches:

```mermaid
flowchart LR
    Raw[Preprocessed private windows] --> Projection[Keyed rank-reduced projection\nand quantization]
    Projection --> Detector[Seizure detector]
    Projection --> Attacker[Patient-ID attacker]
    Detector --> Utility[Detection utility]
    Attacker --> Leakage[Identity leakage]
```

`metadata-scrub` performs metadata de-identification but does not change the
numeric signal. `signal-obfuscation` is experimental risk reduction, not a
formal anonymity guarantee. Encryption protects storage; neither encryption
nor metadata scrubbing removes every possible EEG biometric signal.

## H5 runtime boundary

New Docker installations default to the deterministic development stub. Set
`MODEL_RUNTIME=h5` and `INSTALL_RESEARCH=true` in `.env`, then rebuild, to use
the supplied `best_seizure_model.h5` through the reviewed adapter.
The image is built as `linux/amd64` because the normal
Apple Silicon host environment may not provide the required TensorFlow wheel.
The adapter loads the model once, validates `(None, 1024, 18)` input and
`(None, 1)` sigmoid output, and runs batched float32 predictions.

The checked-in contract is reviewed for the supplied artifact, including its
hash, output semantics, threshold, and training preprocessing. If the H5 file
changes, rerun the verifier and set `reviewed` to false until the replacement
has been reviewed.
The H5 contract starts as an uncalibrated research score. It must not be
presented as confidence, accuracy, or a clinical probability. After separate
patient-disjoint temperature scaling has been fitted for both privacy
profiles, the contract can explicitly activate `calibrated_probability`; the
UI then labels each value as an estimated probability for one four-second
window. The notebook's reported
metrics are also preliminary because its random window split allows adjacent
windows from the same recordings and patients to cross train/test boundaries.

The training notebook uses four-second windows with a two-second step. MDS01
keeps the input tensor unchanged but uses that same 50% overlap when generating
prediction windows. `signal-obfuscation` remains shape-compatible but needs a
separate utility evaluation because the H5 model was trained on the
preprocessed, non-obfuscated signal distribution.

### Profile-specific calibration

Fit calibration only on the fixed `chb07`–`chb08` calibration patients. Run the
command once for each privacy profile and inspect both reports before activating
calibrated output. These are optional research commands for a research-enabled
image, not teammate setup steps. Replace `/absolute/private/chb-mit` below with
your external dataset directory (POSIX shell examples):

```bash
mkdir -p reports
docker compose run --rm --no-deps \
  -v "/absolute/private/chb-mit:/app/chb-mit:ro" \
  -v "$(pwd)/backend/model:/app/backend/model" \
  -v "$(pwd)/reports:/app/reports" \
  backend python backend/scripts/fit_calibration.py /app/chb-mit \
  --privacy-method metadata-scrub \
  --output /app/reports/calibration-metadata-scrub.json \
  --write-contract /app/backend/model/model-contract.json

docker compose run --rm --no-deps \
  -v "/absolute/private/chb-mit:/app/chb-mit:ro" \
  -v "$(pwd)/backend/model:/app/backend/model" \
  -v "$(pwd)/reports:/app/reports" \
  backend python backend/scripts/fit_calibration.py /app/chb-mit \
  --privacy-method metadata-scrub+signal-obfuscation \
  --output /app/reports/calibration-obfuscated.json \
  --write-contract /app/backend/model/model-contract.json
```

These commands store candidates, not reviewed probabilities. The explicit
`--activate` option is for a separate review decision; it is not a substitute
for checking training provenance, exclusions and calibration quality. Do not
activate metadata just to make the UI show a percentage. Rebuild the backend
after changing its bundled contract.

Activation requires both profiles and records the fitted temperature,
calibration subjects, Brier score, ECE, and negative log-likelihood in the
contract. Run the test split evaluator separately for each profile; never use
the test report to fit or select calibration.

## Privacy profile contract

Every upload is protected by encrypted storage and the required metadata scrub.
The optional signal transformation is selected as an ordered list:

```json
["metadata-scrub"]
```

or:

```json
["metadata-scrub", "signal-obfuscation"]
```

The database stores the compact canonical profile
`metadata-scrub` or `metadata-scrub+signal-obfuscation`. The legacy
`privacy_method` form field remains accepted for current canonical values;
historical names are migrated internally and are not returned by the public
API. “None” in the frontend means no optional signal transformation, never
that metadata protection or encrypted storage is disabled.

## Model alerts and timestamps

The model writes one prediction row per four-second window. A recording is
model-positive only when persisted rows have `seizure_detected=true`.
Calibrated output is profile-specific and stored with its calibration version
and dataset. `recording_probability_available` remains `false`: the maximum,
mean, or flagged-window fraction is not a calibrated probability that the
recording contains a seizure.
Optional `.edf.seizures` sidecars and summary files are stored only as private
research metadata; they cannot create, remove, count, color, retain, or label a
model alert.

Positive windows are merged when they overlap or touch. The public recording
response exposes the resulting recording-relative `alert_intervals`, for
example `3560–3576` seconds, plus the flagged-window count. The complete
prediction timeline covers the entire recording. Raw waveform access remains
restricted to bounded retained positive clips and is disabled by default.

## Offline accuracy and research attribution

Live uploads do not have trusted labels, so the routine API never reports an
accuracy percentage. The research evaluator is a separate command:

```bash
PYTHONPATH=. .venv/bin/python backend/scripts/evaluate_chb_mit.py /path/to/chbmit \
  --privacy-method metadata-scrub \
  --split test \
  --output reports/metadata-scrub.json \
  --plots reports/metadata-scrub.png
```

Run it again with
`--privacy-method metadata-scrub+signal-obfuscation` to measure the optional
transformation separately. The evaluator uses the fixed `chb01`–`chb10`
patient manifest, keeps patients disjoint between train/calibration/test
groups, and scores windows only after the recording has been assigned to a
split. `.edf.seizures` sidecars supply labels for this report only; they never
change a live alert. The JSON report includes confusion matrix, ROC/AUC,
precision-recall, sensitivity, specificity, precision, recall, F1, false
alarms per hour, Brier score, ECE, negative log-likelihood, threshold sweep, exclusions, and a
patient-level bootstrap interval.

SHAP attribution is an optional H5-only research feature. Generate the two
profile-specific backgrounds from calibration subjects `chb07` and `chb08`:

```bash
PYTHONPATH=. .venv/bin/python backend/scripts/create_shap_background.py \
  /path/to/chb-mit-scalp-eeg-database-1.0.0
```

The command creates the private, Git-ignored files
`backend/model/shap-background-metadata.npy` and
`backend/model/shap-background-obfuscated.npy`. Set
`ENABLE_SHAP_EXPLANATIONS=true` only after checking both are `(32, 1024, 18)`
`float32` tensors. Docker deliberately excludes these private tensors from its
build context: mount them read-only with a local Compose override and configure
the two `SHAP_*_BACKGROUND_PATH` variables to their container paths. Do not bake
them into an image. The pipeline selects the background matching the final
privacy profile, explains at most the highest-scoring flagged windows, and
returns only channel-level and time-binned aggregates. Missing backgrounds or
SHAP errors fail closed to the normal score-only result. The UI labels this
output “Research attribution — not a clinical explanation.”

## Status lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> validating
    validating --> deidentifying
    validating --> failed
    deidentifying --> preprocessing
    preprocessing --> inference
    inference --> explaining
    explaining --> completed
    explaining --> completed_with_errors
    deidentifying --> completed_with_errors
    preprocessing --> completed_with_errors
    inference --> completed_with_errors
```

`processing_attempts` records stage, status, start/end times, and bounded safe
errors. A failed recording does not stop its siblings.

## API surface

Sessions:

- `POST /api/sessions/upload`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/status`
- `GET /api/sessions/{session_id}/recordings`
- `DELETE /api/sessions/{session_id}` (completed sessions only)

Upload drafts:

- `POST /api/uploads/drafts`
- `GET /api/uploads/drafts/{draft_id}`
- `POST /api/uploads/drafts/{draft_id}/finalize`
- `DELETE /api/uploads/drafts/{draft_id}`

Recordings:

- `GET /api/recordings/{record_id}`
- `GET /api/recordings/{record_id}/prediction`
- `GET /api/recordings/{record_id}/explanation`
- `GET /api/recordings/{record_id}/signal`

Responses expose generated IDs, safe technical metadata, statuses, processing
progress, recording-level model alert counts, predictions, and explanation JSON.
Optional CHB-MIT sidecars are stored only as internal research metadata and are
never returned by normal API responses. Stub results expose a peak window
development score and score timeline, not model confidence or accuracy. A
whole-recording accuracy requires labelled evaluation data. Calibrated
probability is returned only when a reviewed model contract says calibration is
available. The signal route remains `404` unless local preview is explicitly
enabled; even then it only returns bounded retained model-positive clips.
Hidden macOS
archive entries such as `__MACOSX/._*.edf` are ignored before recording rows
are created. A direct recording response also includes its safe
owning `session_id`, `session_created_at`, and `privacy_method` so a recording
result can show when its upload was submitted. They do not expose patient
references, original names, filesystem paths, original files, or cryptographic
hashes.

## Video privacy boundary

Patient-video processing is a separate subsystem, not another EEG recording
stage. Its flow is `video → face redaction → metadata removal + first audio
stream → encrypted output` with no H5 inference, action analysis, or clinical
model call. Audio remains sensitive and owner-only; it is encrypted at rest but
not de-identified.

## Database tables

```mermaid
erDiagram
    SESSIONS ||--o{ RECORDINGS : contains
    SESSIONS ||--o{ PROCESSING_ATTEMPTS : audits
    RECORDINGS ||--o{ PROCESSING_ATTEMPTS : has
    RECORDINGS ||--o{ PREDICTIONS : produces
    PREDICTIONS ||--o{ EXPLANATIONS : explains

    SESSIONS {
        int id PK
        string session_id
        string privacy_method
        string status
        string current_stage
    }
    RECORDINGS {
        int id PK
        string record_id
        int session_db_id FK
        string status
        int sampling_rate
        int channel_count
        string reference_annotation_source_internal
        text reference_intervals_json_internal
        string retained_artifact_path_internal
    }
    PROCESSING_ATTEMPTS {
        int id PK
        int session_db_id FK
        int recording_db_id FK
        string stage
        string status
        datetime started_at
        datetime finished_at
    }
    PREDICTIONS {
        int id PK
        int recording_db_id FK
        float threshold
        float probability
        string score_type
        string calibration_method
        string calibration_version
        string calibration_dataset
        string privacy_method
        boolean seizure_detected
    }
    EXPLANATIONS {
        int id PK
        int prediction_db_id FK
        string method
        boolean is_clinical
        string explanation_data
    }
```

Alembic owns schema changes. Add a new migration instead of changing old
migrations or using `create_all()` in the Docker runtime.

## Backend reading order

1. `app/main.py` — application and routers.
2. `app/api/sessions.py` — upload and session endpoints.
3. `app/services/processing_service.py` — the complete coordinator.
4. `app/services/storage_service.py` — encryption, extraction, cleanup.
5. `app/privacy/deidentify.py` — EDF metadata scrubbing.
6. `app/privacy/signal_projection.py` — shared research transformation and
   PSD attacker features.
7. `app/privacy/retention.py` — positive-window selection and clip creation.
8. `app/eeg/preprocessing.py` and `app/eeg/model_input.py` — model tensor.
9. `app/ml/` — stub and reviewed H5 adapter.
10. `app/database/models/eeg.py` and `app/database/repository.py` — persistence.
11. `migrations/versions/` — database history.
