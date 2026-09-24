# Backend services: a guided tour

This page explains how one request moves through MDS01. It is written for
teammates who want to understand the backend before changing it. It is a
software walkthrough, not a clinical guide; all analysis output is
research-only.

New to the repository? Read [the architecture overview](architecture.md) first,
then [local setup](setup.md) to start the app with one command.

## Start here

- [What runs on the laptop](#what-runs-on-the-laptop)
- [EEG request, step by step](#eeg-request-step-by-step)
- [Backend code map](#backend-code-map)
- [HTTP routes](#http-routes)
- [Video workflows](#video-workflows)
- [Database, files, and deletion](#database-files-and-deletion)
- [Models and explanations](#models-and-explanations)
- [Errors and troubleshooting](#errors-and-troubleshooting)

## What runs on the laptop

Run `node scripts/demo.mjs` from the repository root. The launcher prepares
local configuration without printing secrets, installs frontend packages only
when needed, builds and starts Docker services, waits for the API health check,
then starts the browser UI. It does not register teammate accounts or upload
data. When local-account authentication is enabled, backend startup may seed a
development-only demo administrator; the setup flow generates its password.
The launcher also does not select an EEG/video pairing or claim the modalities
are synchronized. You still sign in and choose the data you are permitted to
use.

| Process/service     | Purpose                                                                      | Data it owns                                                                     |
| ------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Next.js frontend    | Browser pages, upload forms, polling, and review screens                     | Browser state only; it does not store source EEG/video on the server             |
| `postgres`          | Persistent relational database in Docker mode                                | Users, ownership, job/session status, technical result metadata, and predictions |
| `storage-init`      | One-shot permissions setup for the private storage volume                    | No application records; exits after setting directory/file permissions           |
| `vsvig-assets-init` | One-shot pinned model-asset installation and integrity verification          | The external VSViG/OpenPose bundle in a named Docker volume                      |
| `backend`           | FastAPI API, in-process background tasks, migrations, and inference adapters | Encrypted uploads/results in the private storage volume                          |

The frontend runs on the host; the other four rows are Docker Compose services.
The backend waits for PostgreSQL, storage permissions, and the verified VSViG
asset initializer before it starts. EEG H5 assets use a separate named volume.
Model assets stay out of Git and are mounted read-only into the backend.

Native mode is a different profile: SQLite plus local encrypted files and a
host-run FastAPI process. The one-command launcher is for the Docker demo path;
see [setup](setup.md#first-run-native) for native setup.

## EEG request, step by step

```mermaid
sequenceDiagram
    participant UI as Next.js browser
    participant Route as FastAPI route
    participant Auth as Auth/ownership check
    participant Session as Session service
    participant Worker as In-process BackgroundTasks
    participant Store as Private storage
    participant EEG as Validation/privacy/EEG modules
    participant Model as Stub or verified H5 adapter
    participant DB as PostgreSQL or SQLite

    UI->>Route: Upload archive bytes
    Route->>Auth: Resolve cookie/session and owner
    Route->>Store: Encrypt and save upload draft
    Route-->>UI: Opaque draft ID and expiry
    UI->>Route: Finalize draft with privacy profile
    Route->>Session: Create owner-scoped session
    Session->>DB: Save queued status and recording rows
    Route->>Worker: Schedule processing after HTTP response
    Route-->>UI: 202 Accepted + opaque session ID
    Worker->>Store: Decrypt to bounded private work directory
    Worker->>EEG: Validate, scrub metadata, preprocess, build windows
    Worker->>Model: Score the reviewed tensor contract
    Model->>DB: Return scores for persistence
    Worker->>DB: Save status, prediction, and supported explanation
    Worker->>Store: Delete source/transient files; retain only allowed artifact
    UI->>Route: Poll owner-scoped status and review endpoints
```

1. **The browser sends bytes, not a server path.** The upload API receives a
   ZIP as a multipart request. The client cannot choose a storage directory or
   pass a filesystem path.
2. **Authentication resolves the owner first.** In `local-accounts` mode, the
   API reads an opaque HttpOnly cookie, resolves its hashed session token, and
   scopes reads/writes to that account. A guessed ID belonging to someone else
   is returned as not found.
3. **The draft is encrypted and temporary.** `session_service` coordinates
   upload limits, owner quotas, draft expiry, and finalization. `storage_service`
   writes encrypted bytes beneath the configured private storage root. The API
   returns an opaque ID and expiry, not a path or original filename.
4. **Finalization creates an asynchronous session.** The route stores queued
   state and schedules work with FastAPI `BackgroundTasks`, then returns HTTP
   `202`. A long EEG job does not hold the upload request open.
5. **Each recording is validated independently.** The worker checks archive
   bounds and supported file layout, then parses EDF or the supported Nicolet
   format. A malformed recording can fail while valid siblings continue.
6. **Metadata and signal processing stay in backend modules.** Identifying EDF
   metadata is scrubbed; input is mapped to the exact configured bipolar
   montage, resampled to 256 Hz when needed, and prepared as four-second
   windows with a two-second stride. The inference tensor is
   `(N, 1024, 18) float32`.
7. **Inference runs behind one adapter interface.** The default demo runtime is
   `development-stub`; it proves processing wiring, not seizure prediction.
   The H5 option requires a mounted artifact and matching reviewed contract.
8. **Results are persisted before cleanup is reported complete.** Statuses,
   safe technical metadata, prediction windows, and any supported explanation
   are stored through repository/database code. Raw upload contents, original
   metadata, and internal paths are not returned by public serializers.
9. **Transient files are removed.** Cleanup deletes original and intermediate
   EEG files. Retained transformed clips, when policy allows them, are encrypted
   and owner-scoped. Cleanup/recovery also runs on service startup and on a
   bounded schedule.

### Why a job can stop

Validation is intentionally fail-closed. Unsupported montage, malformed EDF or
Nicolet data, invalid timing, missing channels, archive-limit violations, or an
unavailable model contract produce a failed status rather than a plausible
score. A failed recording does not imply a negative seizure result.

## Backend code map

Start at `backend/app/main.py`. It creates FastAPI, installs CORS/body/security
middleware, registers routers, validates the chosen model/auth settings, runs
startup recovery and launches retention sweeps. Routes should translate HTTP
input into service calls; business workflows belong in `backend/app/services/`.

| Area                           | Main files                                                                                                                                                                                                                                                                          | Responsibility                                                                                                                       |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| App/configuration              | [`main.py`](../backend/app/main.py), [`core/config.py`](../backend/app/core/config.py), [`core/middleware.py`](../backend/app/core/middleware.py)                                                                                                                                   | App startup, settings validation, request-size limits, security headers, CORS, and cleanup-task lifecycle                            |
| Authentication/security        | [`api/auth.py`](../backend/app/api/auth.py), [`services/auth_service.py`](../backend/app/services/auth_service.py), [`services/auth_rate_limiter.py`](../backend/app/services/auth_rate_limiter.py), [`core/security.py`](../backend/app/core/security.py)                          | Registration/login, password hashing, session cookies, rate limiting, authentication dependencies, and owner checks                  |
| Upload/session lifecycle       | [`api/uploads.py`](../backend/app/api/uploads.py), [`api/sessions.py`](../backend/app/api/sessions.py), [`services/session_service.py`](../backend/app/services/session_service.py)                                                                                                 | Encrypted upload drafts, per-owner quotas/expiry, session creation/finalization, safe public serializers, and deletion               |
| EEG validation/processing      | [`services/validation_service.py`](../backend/app/services/validation_service.py), [`services/processing_service.py`](../backend/app/services/processing_service.py), [`services/processing_capacity.py`](../backend/app/services/processing_capacity.py)                           | Input validation, bounded concurrency, per-recording stages, prediction persistence, failure recovery, and positive-window retention |
| EEG reading/preprocessing      | [`eeg/io.py`](../backend/app/eeg/io.py), [`eeg/edf_io.py`](../backend/app/eeg/edf_io.py), [`eeg/legacy_nicolet.py`](../backend/app/eeg/legacy_nicolet.py), [`eeg/preprocessing.py`](../backend/app/eeg/preprocessing.py), [`eeg/model_input.py`](../backend/app/eeg/model_input.py) | EDF/Nicolet parsing, exact channel contract, resampling, preprocessing, and tensor construction                                      |
| Privacy/cryptography           | [`privacy/deidentify.py`](../backend/app/privacy/deidentify.py), [`privacy/signal_projection.py`](../backend/app/privacy/signal_projection.py), [`privacy/retention.py`](../backend/app/privacy/retention.py), [`privacy/crypto.py`](../backend/app/privacy/crypto.py)              | Metadata scrubbing, optional research transformation, approved artifact selection, and authenticated encryption                      |
| Prediction/explanations/review | [`api/recordings.py`](../backend/app/api/recordings.py), [`services/explanation_service.py`](../backend/app/services/explanation_service.py), [`services/signal_service.py`](../backend/app/services/signal_service.py), [`ml/`](../backend/app/ml/)                                | Owner-scoped results, optional bounded signal view, score summary, and supported non-clinical explanation payloads                   |
| Case summaries                 | [`api/cases.py`](../backend/app/api/cases.py), [`services/case_service.py`](../backend/app/services/case_service.py)                                                                                                                                                                | Opaque owner-scoped grouping of separate modality jobs; no patient-derived identifier                                                |
| Video detection                | [`api/video_detection.py`](../backend/app/api/video_detection.py), [`services/video_detection_service.py`](../backend/app/services/video_detection_service.py), [`video_detection/`](../backend/app/video_detection/)                                                               | Encrypted job lifecycle, strict runtime/pose/model contract checks, scores, and privacy-safe visualization                           |
| Video privacy utility          | [`api/video_privacy.py`](../backend/app/api/video_privacy.py), [`services/video_privacy_service.py`](../backend/app/services/video_privacy_service.py), [`video_privacy/processor.py`](../backend/app/video_privacy/processor.py)                                                   | Separate face-redaction workflow; strips audio/metadata from retained output and does not run seizure inference                      |
| Video storage                  | [`services/video_storage_service.py`](../backend/app/services/video_storage_service.py)                                                                                                                                                                                             | Private encrypted video artifacts, bounded materialization, and cleanup-aware responses                                              |
| Database/migrations            | [`database/db.py`](../backend/app/database/db.py), [`database/repository.py`](../backend/app/database/repository.py), [`database/models/`](../backend/app/database/models/), [`migrations/versions/`](../backend/migrations/versions/)                                              | SQLModel engine/session, persistence queries, tables/relations, and Alembic schema history                                           |
| Research-only tools            | [`research/`](../backend/app/research/), [`backend/scripts/`](../backend/scripts/)                                                                                                                                                                                                  | Offline evaluation, calibration analysis, dataset tooling, and runtime verifiers; not the request-serving API                        |

### Service modules, in plain language

These modules are the main workflow owners in `backend/app/services/`:

| Module                       | What it does                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `auth_service.py`            | Creates local accounts, hashes/verifies passwords, issues and revokes session tokens, and maps Cloudflare identities to owner rows.        |
| `auth_rate_limiter.py`       | Bounds repeated login/registration attempts without allowing its in-memory buckets to grow forever.                                        |
| `case_service.py`            | Creates opaque case IDs and assembles safe, owner-filtered EEG/video summaries.                                                            |
| `explanation_service.py`     | Converts available per-window scores into a descriptive summary; it does not diagnose or invent an attribution method.                     |
| `processing_capacity.py`     | Limits admitted concurrent EEG work so one local backend cannot run unbounded analyses.                                                    |
| `processing_service.py`      | Coordinates the EEG background job, records stage outcomes, persists predictions, retains approved transformed evidence, and cleans up.    |
| `session_service.py`         | Owns upload drafts, expiry/quota handling, session/recording lifecycle, public payload shaping, and owner-scoped deletion.                 |
| `signal_service.py`          | Builds a bounded waveform response only when the configured preview policy allows it.                                                      |
| `storage_service.py`         | Extracts supported archives into private work areas, encrypts/decrypts EEG files, and removes transient material.                          |
| `validation_service.py`      | Checks the selected EEG file format and verifies the technical recording requirements before processing.                                   |
| `video_detection_service.py` | Coordinates admission, preprocessing, pose/model execution, result retention/expiry, failure state, and cleanup for VSViG jobs.            |
| `video_privacy_service.py`   | Coordinates the separate face-redaction job, validates the transformed output, and handles acknowledgement, download, expiry, and cleanup. |
| `video_storage_service.py`   | Encrypts, materializes, and deletes video files; its response helper removes temporary plaintext after streaming.                          |

`api/` modules are the HTTP layer. `database/repository.py` and
`database/video_detection_repository.py` own query logic. `database/models/`
contains stored rows. Change the schema only with a new Alembic migration; do
not rely on runtime `create_all()`.

## HTTP routes

All routes below are prefixed exactly as shown. Health and login/session
bootstrap routes are public; EEG, case, and video workflows require an
authenticated owner in the normal local demo configuration.

| Feature         | Routes                                                                                                                                                                                                                                                      | Purpose                                                                                                            |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Health          | `GET /health`                                                                                                                                                                                                                                               | Backend process health response used by the launcher and operators                                                 |
| Authentication  | `GET /api/auth/session`, `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`                                                                                                                                                         | Create/revoke local sessions or inspect current login                                                              |
| Upload drafts   | `POST /api/uploads/drafts`, `GET /api/uploads/drafts/{draft_id}`, `POST /api/uploads/drafts/{draft_id}/finalize`, `DELETE /api/uploads/drafts/{draft_id}`                                                                                                   | Stage encrypted EEG ZIP bytes, inspect expiry, start processing, or cancel a draft                                 |
| EEG sessions    | `POST /api/sessions/upload`, `GET /api/sessions`, `GET /api/sessions/{session_id}`, `GET /api/sessions/{session_id}/status`, `GET /api/sessions/{session_id}/recordings`, `DELETE /api/sessions/{session_id}`                                               | Direct asynchronous upload plus owner-scoped session listing, status, and deletion                                 |
| Recordings      | `GET /api/recordings/{record_id}`, `/prediction`, `/annotations`, `/explanation`, `/signal`                                                                                                                                                                 | Safe technical result, score windows, sanitized event markers, explanation summary, or policy-gated signal preview |
| Cases           | `GET /api/cases`, `GET /api/cases/{case_id}`                                                                                                                                                                                                                | Opaque longitudinal grouping; EEG/video analyses remain independent                                                |
| Video detection | `POST /api/video-detection/jobs`, `GET /api/video-detection/jobs`, `GET /api/video-detection/jobs/{job_id}`, `GET /api/video-detection/jobs/{job_id}/predictions`, `GET /api/video-detection/jobs/{job_id}/visualization`                                   | Submit a separate visual-only VSViG review and inspect owner-scoped results                                        |
| Video privacy   | `POST /api/video-privacy/jobs`, `GET /api/video-privacy/jobs`, `GET /api/video-privacy/jobs/{job_id}`, `POST /api/video-privacy/jobs/{job_id}/acknowledge`, `GET /api/video-privacy/jobs/{job_id}/preview`, `GET /api/video-privacy/jobs/{job_id}/download` | Run the independent privacy transform and retrieve its protected output when policy permits                        |

The old `/api/v1` prototype routes are removed. Public serializers deliberately
omit source filenames, patient references, raw annotation text, cryptographic
hashes, and server filesystem paths. The signal preview route can return `404`
when previews are disabled or no policy-approved artifact exists.

## Video workflows

Video detection and the standalone privacy utility are different workflows.
They do not share a model or a result interpretation.

### VSViG video detection

`POST /api/video-detection/jobs` creates an encrypted owner-scoped job. The
backend checks the media, normalizes timing/geometry only when the configured
contract allows it, and gives the same full-frame-blurred protected frames to
Lightweight OpenPose and VSViG. Keypoints are converted to the pinned model's
patch input; the model produces window scores and a review timeline. A separate
audio-free, privacy-safe visualization may be retained encrypted until its
expiry. Original and protected model-input plaintext are removed after success
or failure.

This path fails closed for unsupported geometry/timing, missing or ambiguous
pose, invalid model input/output, missing or mismatched assets, and failed
privacy visualization. Do not disable these checks merely to get a demo score.
The pinned default expects 1920×1080; smaller-source adaptation remains an
explicit operator choice. See [the detailed video contract](video-detection.md).

### Standalone video privacy

`POST /api/video-privacy/jobs` selects the face-redaction utility. It does not
run VSViG or EEG inference. The retained transformed output is encrypted,
audio-free, and stripped of source metadata; source and temporary plaintext are
cleaned up. Intermittent redaction requires acknowledgement before download.
See [the video privacy/runbook notes](video-detection.md#privacy-and-retention)
for the current policy and limitations.

## Database, files, and deletion

| Information                                                                     | Stored in                                        | Lifetime / access                                                                      |
| ------------------------------------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Users, hashed auth sessions, owners, case IDs, job/session state                | SQLite in native mode; PostgreSQL in Docker mode | Persistent database rows; owner filters apply to normal API reads                      |
| Predictions, score summaries, allowed explanation data, safe technical metadata | Database                                         | Retained with the review record; labeled research-only                                 |
| Uploaded EEG/video bytes and transformed media                                  | Private filesystem-backed volume                 | Encrypted at rest; never stored as database blobs or exposed as server paths           |
| Decrypted work files and source media                                           | Private temporary work directory                 | Removed after processing; startup/scheduled sweeps recover interrupted or expired work |
| EEG positive-window artifact, where enabled by retention policy                 | Private encrypted storage                        | Owner-scoped and retained only under the configured policy                             |
| Video detection visualization and predictions                                   | Encrypted private storage plus result metadata   | Retained to the job expiry; source and protected model-input video are deleted         |
| Standalone protected video and preview                                          | Encrypted private storage                        | Retained to expiry; audio is not retained                                              |

The encryption keys are local installation secrets. `node scripts/setup.mjs`
creates them once; the demo launcher preserves existing nonempty values and
never prints them. Losing/changing a key can make retained files unreadable.
Never run `docker compose down -v` unless you intentionally want to delete the
PostgreSQL and encrypted-storage volumes.

The backend uses FastAPI `BackgroundTasks` and bounded in-process capacity,
not a durable queue. A backend restart can interrupt active work; startup
recovery marks/reconciles interrupted jobs and removes stale private files.
Run one backend process for this prototype. Multiple workers require a durable
queue and shared concurrency/cleanup design first.

## Models and explanations

### EEG

The reviewed tensor contract is 256 Hz, the exact 18 configured bipolar
channels, four-second windows, a two-second stride, and `(N, 1024, 18)`
`float32` input. `MODEL_RUNTIME=stub` selects `development-stub` / `stub-0.1.0`
with threshold `0.5`; its output is deterministic development data. It is not
seizure detection, a calibrated probability, or clinical evidence.

`MODEL_RUNTIME=h5` selects an operator-mounted model. At startup the backend
validates the artifact, hash, runtime dependencies, and reviewed contract; it
fails startup rather than accepting uploads if that configuration is invalid.
The contract must be reviewed before making claims about calibration or
performance. SHAP output is available only when an approved background and
runtime support it; absence of SHAP is not filled with a fabricated explanation.

### Video

Video detection uses the pinned VSViG and Lightweight OpenPose runtime contract.
The backend verifies external assets before serving detection. Pose-coverage,
timing, geometry, and model-output checks can reject a video; rejection means
“no supported result,” not “no seizure.” There is no EEG/video score fusion.

For both modalities, use explanations as review aids, not diagnosis. The report
can show model/config provenance, event timing, flagged windows, privacy
processing status, and limitations when those fields actually exist. Pairing
and clock offset remain assumed unless independently established.

## Errors and troubleshooting

| What you see                                      | What it means                                                                     | Safe next check                                                                                                        |
| ------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Launcher says Docker Compose is unavailable       | Docker Desktop is stopped or the Compose plugin is missing                        | Start Docker Desktop, then run `docker compose version`                                                                |
| Backend health never becomes ready                | Build, migrations, model-asset verification, or startup failed                    | Run `docker compose ps` and `docker compose logs backend`; do not paste secrets from `.env`                            |
| `401` from a protected route                      | No active local session/cookie                                                    | Create an account or sign in in the browser                                                                            |
| `404` for a resource ID                           | The record does not exist for this owner, or the optional artifact is unavailable | Use the signed-in account that submitted it; IDs do not grant access                                                   |
| EEG validation/format failure                     | The archive or recording does not meet the supported format/contract              | Review the upload format and sanitized technical status; do not infer a negative result                                |
| Video `incomplete_pose` or ambiguous-pose failure | Pose coverage/framing did not satisfy the pinned runtime gate                     | Use a shorter, supported clip with one visible subject and better framing; do not weaken the gate                      |
| Video timing/geometry rejection                   | The media does not meet the pinned timing/resolution contract                     | Inspect the documented supported input; smaller geometry needs explicit reviewed adaptation                            |
| Model contract/hash failure                       | Required model bundle is absent, changed, or not verified                         | Follow the pinned installer and verifier in [video detection](video-detection.md); never copy private weights into Git |
| Output says `development-stub`                    | EEG processing used the deterministic demo adapter                                | Label scores as development-only; do not present them as real model predictions                                        |
| No SHAP explanation appears                       | SHAP is disabled or the reviewed background/runtime is unavailable                | Explain only the evidence the active adapter actually produces                                                         |

## Suggested reading order in code

To follow one EEG upload from the browser to the final response:

1. [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) — browser request
   construction and response parsing.
2. [`backend/app/api/uploads.py`](../backend/app/api/uploads.py) — HTTP
   request parsing, authentication dependency, status/error translation.
3. [`backend/app/services/session_service.py`](../backend/app/services/session_service.py)
   — draft quota, encryption handoff, finalization, and session creation.
4. [`backend/app/services/processing_service.py`](../backend/app/services/processing_service.py)
   — per-record processing coordinator and failure/cleanup rules.
5. [`backend/app/services/storage_service.py`](../backend/app/services/storage_service.py)
   and [`backend/app/privacy/crypto.py`](../backend/app/privacy/crypto.py) —
   encrypted storage and transient file boundaries.
6. [`backend/app/eeg/`](../backend/app/eeg/) and
   [`backend/app/privacy/`](../backend/app/privacy/) — parsing, metadata
   handling, tensor preparation, and approved retention.
7. [`backend/app/ml/model_loader.py`](../backend/app/ml/model_loader.py) —
   selected inference adapter.
8. [`backend/app/database/repository.py`](../backend/app/database/repository.py)
   and [`backend/app/api/recordings.py`](../backend/app/api/recordings.py) —
   stored results and owner-filtered public projection.

For the full technical contract and research utilities, continue to
[Backend internals](backend.md). For route schemas, open the local Swagger UI at
`http://127.0.0.1:8000/docs` after starting the app.
