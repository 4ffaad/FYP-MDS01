# MDS01 Engineering Guide

This repository contains the FastAPI backend and a separate Next.js frontend.
Frontend visual work belongs under `frontend/`; backend changes must preserve
the API privacy boundaries described below.

## Architecture

The backend flow is:

```text
EEG ZIP upload → FastAPI → PostgreSQL session → FastAPI BackgroundTasks
  → encrypted source retention → validation → model-input de-identification
  → preprocessing → inference adapter → explanation artifact → PostgreSQL results

video upload → encrypted original → owner reference copy (independent of model)
  separate VSViG analysis → first-window OpenPose readiness → queue → normalization
  ├→ transient normalized frames → OpenPose keypoints + 15 RGB patches
  │                                  → VSViG → predictions
  └→ source video → audio-free H.264 review copy → encrypted storage
```

FastAPI routes must remain thin. Business logic belongs in services,
database access belongs in repositories, and long-running EEG work belongs in
`backend/app/services/processing_service.py` and is scheduled through FastAPI
BackgroundTasks.

## Repository map

- `backend/app/main.py` configures FastAPI, auth, routers, startup validation,
  and retention/recovery tasks.
- `backend/app/api/` contains HTTP routes; `backend/app/services/` owns upload,
  processing, auth, case, storage, explanation, and cleanup workflows.
- `backend/app/database/` contains SQLModel models, the engine/session helper,
  and repositories. Schema history lives in `backend/migrations/versions/`.
- `backend/app/eeg/`, `privacy/`, and `ml/` implement EEG input, privacy, and
  inference. `video_privacy/` is a separate transform; `video_detection/`
  validates and runs the pinned VSViG/pose pipeline. Offline evaluation and
  calibration code lives in `backend/app/research/` and `backend/scripts/`.
- `frontend/src/app/` uses the Next.js App Router; `components/` holds screens
  and UI, and `lib/` holds the API adapter, types, and client workflows.
- `scripts/` contains local setup and launchers. `docs/README.md` maps the
  setup, architecture, backend, frontend, design, and video runbooks.

## Runtime, database, and commands

- `docker-compose.yml` is the team runtime: PostgreSQL 16, the backend,
  private storage initialization, and VSViG asset initialization. The backend
  runs Alembic before Uvicorn. The local research profile uses the reviewed H5
  EEG model; video detection uses the separately verified external VSViG bundle.
- Native mode uses SQLite and local encrypted storage. `scripts/start-native.mjs`
  applies Alembic before starting FastAPI. `docker-compose.local-research.yml`
  opts into the local H5 profile. The video-detection Compose file is an empty
  compatibility overlay; the main Compose file owns that service. The security
  Compose file is a separate disposable test stack.
- From the repository root, `node scripts/demo.mjs` selects the real local H5
  research profile and requires its ignored model and reviewed contract;
  `node scripts/demo.mjs --development-stub` selects synthetic scores for
  workflow-only demos. Plain `docker compose up --build` builds and starts the
  base stack. Native startup uses `node scripts/setup.mjs`, then
  `node scripts/start-native.mjs`.
- Backend tests use stdlib `unittest`:
  `PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v`.
  Launcher checks use `node --test scripts/setup.test.mjs` and
  `node --test scripts/start-native.test.mjs`.
- From `frontend/`, use `npm run dev` for development and `npm run build` for
  the production build. Frontend checks are `npm run format:check`,
  `npm run lint`, `npx next typegen`, `npx tsc --noEmit`, and
  `npm run test:e2e`. Auth, report-API, and real-service browser suites have
  separate `test:e2e:auth`, `test:e2e:report`, and `test:e2e:real` scripts.
  See `docs/setup.md` for prerequisites and runtime-specific details.

## Privacy boundaries

- Keep EEG binaries outside PostgreSQL.
- Store files beneath `backend/storage/sessions/{session_id}/`.
- Never expose patient references, original metadata, filesystem paths, or
  original files through public API responses.
- Retain each uploaded EEG archive, each original recording, and any source
  report encrypted until the owning account deletes its case. Retain complete
  readable source channels, timing, gaps, and annotations. APIs expose them only
  to the owner through protected download and waveform routes. Temporary
  plaintext is removed after each read or processing step. Keep all binaries
  outside PostgreSQL; keep encryption keys outside Git and separate from backups.
  Historical cases keep their recorded policy and availability state; files
  already deleted cannot be recovered.
- The dashboard offers combined, EEG-only, and video-only intake. Combined EEG
  and video work shares one patient case; EEG-only intake allows an optional
  report and never submits selected video files.
- Combined uploads retain encrypted original video for owner-only reference
  playback. This path makes an audio-free H.264 browser copy without requiring
  OpenPose readiness or VSViG admission. Unmatched clips remain playable and
  show their alignment status. Separate VSViG analysis still requires the pinned
  model's pose and input gates, uses unblurred RGB patches, and preserves its
  exact model contract. New analysis and reference videos are unblurred; labels
  remain accurate for historical blurred outputs. Delete normalized frames,
  extracted patches, and temporary plaintext after processing. Retain encrypted
  originals, review videos, and results until case deletion. Every media, result,
  waveform, report, and download request is owner-scoped and private/no-store.
  The ten-minute decrypted video range cache remains private and is cleaned up
  when idle. The separate video-privacy utility keeps its documented policy.
- For combined legacy Nicolet `.e` and AVI folder uploads, keep only a
  case-scoped HMAC of each referenced basename and an opaque camera-folder
  group ID. Encrypt VEEG frame/clock anchors and resolved offsets at rest.
  Finalize a folder only when the accepted clip count matches the selected
  count. Serialize owner-scoped resolver/finalizer mutations with the owner
  row lock. Link a clip only when its filename token, frame count, frame rate,
  and clock anchors produce one unique metadata match; leave incomplete or
  ambiguous clips unpaired. Present this as a unique metadata match among
  uploads, not proof of original byte identity. Use EEG source-clock positions
  for aligned timelines, preserve acquisition gaps, and disclose partial clip
  coverage. This parser is validated against supplied recordings, not an
  official Nicolet-format specification.
- Do not log patient-identifying values.
- Review EDF start dates and annotations before changing de-identification
  policy; they may contain sensitive timing information.
- Do not hard-code secrets or encryption keys.

## Processing contract

The reviewed model-input contract is 256 Hz, the exact 18 configured bipolar
channels, four-second windows with a two-second stride, and `(N, 1024, 18)`
`float32` input. The local research profile must use H5 and validate the
artifact hash and reviewed contract at startup. Do not use stub inference for
the patient workflow.

Do not invent a real model architecture, output contract, preprocessing
parameters, or clinical explanation method. For video, use the pinned VSViG
and Lightweight OpenPose contract in `docs/video-detection.md`; do not replace
its source or checkpoints. The optional `VSVIG_ALLOW_LETTERBOX_ADAPTATION`
research path is disabled by default; preserve its provenance and never treat
adapted inputs as validated equivalents to native 1920×1080 inputs.

## API

The API exposes authentication under `/api/auth/`, owner-protected
cases/patient profiles and EEG sessions/uploads/recordings, a separate video
privacy utility, and independent video-detection resources. The primary EEG
workflow is asynchronous:

```text
POST /api/sessions/upload
POST /api/uploads/drafts
GET  /api/uploads/drafts/{draft_id}
POST /api/uploads/drafts/{draft_id}/finalize
DELETE /api/uploads/drafts/{draft_id}
GET  /api/sessions
GET  /api/sessions/{session_id}
GET  /api/sessions/{session_id}/status
GET  /api/sessions/{session_id}/recordings
GET  /api/recordings/{record_id}
GET  /api/recordings/{record_id}/prediction
GET  /api/recordings/{record_id}/explanation
GET  /api/recordings/{record_id}/signal
GET  /api/cases
GET  /api/cases/{case_id}
DELETE /api/cases/{case_id}
GET  /api/cases/{case_id}/patient-profile
PUT  /api/cases/{case_id}/patient-profile
DELETE /api/cases/{case_id}/patient-profile
POST /api/video-privacy/jobs
GET  /api/video-privacy/jobs
POST /api/video-detection/preflight
POST /api/video-detection/jobs
POST /api/video-detection/cases/{case_id}/sync-groups/{group_id}/finalize
GET  /api/video-detection/jobs
GET  /api/video-detection/jobs/{job_id}
GET  /api/video-detection/jobs/{job_id}/visualization
GET  /api/video-detection/jobs/{job_id}/predictions
```

The old `/api/v1` prototype routes have been removed. EEG changes use the
asynchronous session and recording API; video detection remains an independent,
owner-filtered workflow. Its optional Nicolet sync mapping is a metadata link,
not a combined model or diagnosis. EEG processing-stage history is serialized as
safe stage/status/timing metadata only; do not add source filenames or error
details.

The VEEG sync-group finalize request body includes `expected_source_names`; the
server compares their case-scoped HMAC multiset with accepted group uploads
before finalization. Raw names are transient and must never be persisted,
logged, or returned.
The browser respects video queue capacity and retries only a clip that received
an explicit not-accepted response. Whole-case deletion removes its linked EEG and video
jobs, retained files, patient profile, and source report; it returns `409` while
any linked processing job is active.

## Test coverage and risk areas

- Backend tests are stdlib `unittest`; most database tests use temporary
  in-memory SQLite, and model/runtime tests use synthetic or mocked assets.
  They do not by themselves verify PostgreSQL behavior or real model outputs.
- The default Playwright configuration uses the browser API stub. Use the
  dedicated report/auth/real suites when changing their backend integration.
- No CI workflow is checked into this repository. Run the relevant local
  checks and record which runtime/profile they cover.
- The default demo uses the reviewed H5 EEG profile; keep setup documentation
  aligned with its explicit stub-only alternative.
- Authentication and owner filtering, upload/archive parsing, EDF metadata
  handling, encrypted file cleanup/retention, model-contract validation, and
  video admission/model assets are privacy or data-loss boundaries. Keep their
  regression tests current and verify the affected runtime profile; never
  treat a stub or synthetic fixture as evidence about clinical performance.

## Development rules

1. Inspect the existing code before creating a module.
2. Preserve working behavior and existing user changes.
3. Add tests for new validation, privacy, processing, and API behavior.
4. Use Alembic migrations; do not rely on production startup `create_all()`.
5. Use PostgreSQL in Docker Compose; schedule prototype processing with
   FastAPI BackgroundTasks.
6. Keep H5 inference behind the validated model contract and fail closed when
   the artifact, hash, runtime, or reviewed preprocessing contract is invalid.
7. Keep VSViG assets outside Git, install them with the pinned installer, and
   run the model verification command before enabling video detection.
8. Treat all outputs as research-only; label stub predictions as development data.
9. For frontend work, follow `frontend/AGENTS.md` (including its installed
   Next.js documentation requirement) and `DESIGN.md`.
