# MDS01 project design

**Last reviewed: 2026-10-28**

This document describes the system that exists in the repository. It is the
technical design record for maintenance and integration; it does not
claim that the research models are clinically validated or that the prototype
is ready for hospital deployment.

## Purpose and scope

MDS01 is a local research prototype for reviewing EEG recordings, synchronizing
verified video clips to EEG source time, and presenting separate research-model
findings. Its users can inspect source waveforms, imported annotations, and
flagged model windows. Owner-observation endpoints exist, but the current
frontend does not expose an observation editor. The system does not diagnose
seizures, infer seizure onset from movement side, or combine EEG and video
scores.

The main workflows are combined EEG/VEEG review, EEG-only analysis, and a
separate experimental video-analysis demo. Combined video review does not run
OpenPose or VSViG. The standalone video workflow does not become synchronized
with EEG just because both modalities exist in one case.

## Platforms and components

| Layer          | Implementation                                  | Responsibility                                                                           |
| -------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Browser        | Next.js App Router, React, TypeScript           | Intake, case history, EEG canvas, playback, timelines, and annotations                   |
| API            | FastAPI and Python                              | Authentication, validation, upload orchestration, protected reads, and processing status |
| Database       | PostgreSQL 16 in Compose; SQLite in native mode | Accounts, cases, job state, safe metadata, annotations, and model results                |
| File storage   | Private local filesystem or Docker volume       | Encrypted EEG archives, source recordings, video, and derived artifacts                  |
| Schema changes | Alembic                                         | Versioned database migrations                                                            |
| Async work     | FastAPI `BackgroundTasks`                       | Prototype EEG processing; bounded background and owner-priority VEEG playback preparation; serialized standalone video inference |
| EEG runtime    | Keras H5 adapter                                | Loads only the external model artifact and reviewed contract                             |
| Video runtime  | Pinned VSViG and Lightweight OpenPose bundle    | Separate experimental pose and video inference                                           |

The [backend security sequence diagrams](architecture.md) show login, storage
encryption, model processing, and authorized decryption, with links to the
source files responsible for each protection.

Routes validate requests and build responses. Service modules own workflows;
repositories own database queries. EEG and video binaries stay outside the
relational database.

## EEG intake, processing, and display

Uploads enter through the owner-scoped session or staged-upload API. The server
retains encrypted source material before processing, validates each supported
recording, builds a separate model input, and records per-window scores and
processing state. Supported source paths include EDF/EDF+, the reviewed legacy
Nicolet `.e` layout, and Nicolet `.data` with its `.head` sidecar. A failure on
one recording does not become a negative seizure result.

The H5 model contract is fixed at 256 Hz, 18 named bipolar channels in the
reviewed order, four-second windows, and a two-second stride. Model inputs are
finite `float32` arrays shaped `(N, 1024, 18)`. The current preprocessing code
applies a 0.5–100 Hz bandpass, a 60 Hz notch, per-channel z-score normalization,
and clipping at ±5 before window inference. Nicolet `.e` ingestion supports the
reviewed 33-channel, referential, 500 Hz delivery layout; it derives the
configured bipolar channels, resamples to 256 Hz, and creates a separate
scrubbed EDF for model processing. These transformations never replace the
retained original.

The H5 file, reviewed model contract, and independent hashes are local assets,
not repository files. Startup validates their shapes, channel order, sampling
rate, output, and hashes. Missing or mismatched assets fail closed. The
development stub exists only for synthetic workflow demos. Scores are
research outputs; the supplied contract is not treated as calibrated clinical
probability.

The clinical display reads bounded ranges from retained source data. It opens
on a fixed 12-second page with the longitudinal bipolar montage, 100 µV/cm,
30 mm/s, and 0.5–70 Hz plus a 50 Hz notch when supported by the source rate.
The source is not normalized to make it look cleaner. A gap with no acquired
samples remains an empty interval on the source clock. The HUKM-style montage,
channel colors, physical-unit conversion, and display limits are described in
the [EEG walkthrough](inference-walkthrough.md#eeg-waveform-display).

## Combined EEG/VEEG review

Combined uploads keep original EEG and video encrypted in private storage. EEG
inference runs on its own processing path. When
`MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true`, an owner can open the reference
video popup. Upload encrypts and stores the original, then acknowledges without
probing, decrypting, or converting the video. A restart-recoverable background
worker checks clock/format metadata and refreshes sync mappings; it does not run
pose estimation or VSViG. New video originals use authenticated AES-256-GCM
chunks, so browser-compatible originals stream only the requested byte ranges.
The metadata worker records whether the source is browser-compatible. An
unsupported clip stays encrypted and is converted to an audio-free H.264 review
copy only after its owner opens the popup.
Originals and derived review files remain encrypted until case deletion. The `.env.example`
template enables this for the local owner-only demo. A backend started without
the setting defaults to disabled.

For supported legacy Nicolet/AVI folder uploads, synchronization uses a
case-scoped HMAC of the source-name token, encrypted clock/frame anchors, frame
count, and frame rate. A clip is linked only when the upload group is complete
and the metadata yields one unique match. There is no fuzzy name match or
guessed offset. The EEG source clock is the authoritative shared timeline.
Verified video remains on that clock across internal EEG acquisition gaps;
the EEG trace still shows no samples in those intervals. Clips without a
verified mapping remain available as independent reference video when the
review setting is enabled, with their alignment status shown.

The review popup is opt-in and remains open until the user closes it. Compatible
H.264 MP4 originals with optional AAC audio stream directly. After the
background metadata probe, unsupported clips remain encrypted and unconverted
until the owner opens playback. This does not run VSViG. The EEG source clock drives verified video
seeking, playback state, and playback rate; it holds during buffering, and
routine video time updates do not reset it. The player supports slow motion,
frame stepping, and timestamped bookmarks. The UI distinguishes source
annotations and model flags. Owner-observation endpoints remain available in the
backend API, but annotation entry is not exposed in the current UI.

## Standalone VSViG experiment

The separate Video workflow encrypts the uploaded source before private-file
storage, then decrypts it only in the temporary worker workspace. It normalizes
supported input to the pinned model contract, samples at 6 frames per second,
estimates multiple people with
Lightweight OpenPose, and builds 30-frame windows with a three-frame stride.
The model input contains 15 selected joints and 15 RGB patches per sample:
patch tensors have shape `[B, 30, 15, 3, 32, 32]`; pose coordinates and
confidence have shape `[B, 30, 15, 3]`. A scored window needs all selected
landmarks for one person at every sample. Missing joints are not invented or
interpolated. Each detected person is processed as a separate track; automatic
track identity is not guaranteed, and the model does not identify which track
is the patient.

Native 1920×1080 inputs follow the pinned preprocessing path. Lower-resolution
letterbox adaptation is an experimental opt-in and is disabled by default.
Outputs are uncalibrated research scores. The local demo clip and HUKM clinical
review are separate evidence paths; pose failure cannot block reference
playback. Exact pinned assets, hashes, preprocessing details, and known pose
limits live in the [video runbook](video-detection.md).

The VSViG result, including window scores and Grad-CAM evidence, is compressed
and AES-256-GCM encrypted in PostgreSQL, bound to the owner and job ID. Video
binaries remain encrypted in private file storage. The owner-authorized results
API decrypts the stored result for display; case deletion removes it.

The separate `/api/video-privacy/` utility supports its own configured
de-identification workflow. It is not part of combined VEEG review or the
VSViG inference path.

## API design

The running FastAPI OpenAPI document at `/docs` is authoritative for request
and response schemas. The main route groups are:

| Route group                                 | Main operations                                                                                                            |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `/api/auth/`                                | Register, log in/out, and inspect the current session                                                                      |
| `/api/uploads/`                             | Stream upload drafts, inspect, finalize, or cancel them                                                                    |
| `/api/sessions/`                            | List and inspect EEG sessions, status, recordings, source archive, and delete                                              |
| `/api/recordings/`                          | Read recording metadata, prediction windows, source annotations, optional attribution, bounded waveform, and original file |
| `/api/recordings/{id}/clinical-annotations` | Add, list, and delete encrypted owner observations                                                                         |
| `/api/cases/`                               | List, read, and delete cases; read/update profiles and source reports                                                      |
| `/api/video-detection/`                     | Preflight and upload video, finalize sync groups, read jobs/predictions, stream protected playback, download original      |
| `/api/video-privacy/`                       | Create and review independent de-identification jobs                                                                       |
| `/health`                                   | Public health status only                                                                                                  |

All clinical-data endpoints are authenticated and owner-scoped. Media streams
support protected byte ranges, use private/no-store responses, and do not
expose filesystem paths. Clinical observations are encrypted in the database.
The access-event table stores allowlisted actions and internal row IDs, not
patient labels, names, filenames, paths, IP addresses, or media.

## Data protection and limits

Encrypted files use authenticated AES-GCM envelopes bound to their storage
location. PostgreSQL holds structured state and results, not recording bytes.
Temporary plaintext and intermediate model artifacts are removed after use;
case deletion removes linked metadata and retained files. Keys are configured
outside Git and must be backed up separately from encrypted data.

The current account model is uploader-only; shared clinician roles are not
implemented. Background tasks run inside the API process and are not a durable
queue, so a restart can interrupt active work. Local Compose binds services to
loopback. HTTPS termination, institutional identity, key rotation, and tested
backup recovery are deployment work before exposing the system outside a
trusted local environment.

## Running and verification

The standard local stack requires Docker Desktop, Node.js 22+, and internet
access to initialize pinned video assets. Run:

```sh
node scripts/setup.mjs
# Put the independently reviewed H5 model, contract, and their configured
# hashes in the ignored local asset location described by docs/setup.md.
node scripts/demo.mjs
```

The default local demo selects the real H5 profile. The explicit
`node scripts/demo.mjs --development-stub` option is for synthetic workflow
checks only. Native mode uses SQLite through `node scripts/start-native.mjs`.
See [setup](setup.md) for the exact model files, environment variables, and
alternate commands.

Backend tests use `PYTHONPATH=. .venv/bin/python -m unittest discover -s
backend/tests -v`. Frontend checks run from `frontend/`: `npm run format:check`,
`npm run lint`, `npx next typegen`, `npx tsc --noEmit`, `npm run test:e2e`, and
`npm run build`. Browser API-stub tests do not validate live inference or
clinical performance. The codebase's current verified behavior and remaining
work are summarized in [`tasks/plan.md`](../tasks/plan.md).

## Design references

- [Project goal](project-goal.md) — intended outcome and scope.
- [Architecture diagrams](architecture.md) — component and VEEG flow.
- [EEG inference and display](inference-walkthrough.md) — signal details and
  research-score interpretation.
- [Backend guide](backend.md) — services, storage, and route implementation.
- [Frontend guide](frontend.md) — screens and browser behavior.
- [Setup guide](setup.md) — prerequisites and local run commands.
- [Video runbook](video-detection.md) — pinned VSViG contract and limits.
