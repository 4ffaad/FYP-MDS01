<!-- bmad:context -->
<!-- Verified 2026-08-26 against f0f5443 (plus current working tree). Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep preserved rules outside the markers. -->

## MDS01

Research-only EEG review workspace with FastAPI/PostgreSQL backend and Next.js frontend. Shared project knowledge lives in `docs/`; BMad planning and implementation artifacts live in `_bmad-output/`. Root context covers both backend and frontend; child-specific rules remain in `frontend/AGENTS.md`.

## Where things are

- Backend routes: `backend/app/api/`; services: `backend/app/services/`; repositories/models: `backend/app/database/`; EEG/privacy/model code: `backend/app/eeg/`, `backend/app/privacy/`, `backend/app/ml/`.
- Backend details: `docs/backend.md`; setup commands: `docs/setup.md`; frontend details: `docs/frontend.md`; security/privacy: `docs/security-audit.md` and `docs/privacy-research.md`.
- Frontend entry points: `frontend/src/app/`, `frontend/src/components/`; API boundary: `frontend/src/lib/api.ts`; visual contract: `DESIGN.md`.
- BMad configuration: `_bmad/`; use `bmad-help` for workflow selection and `bmad-project-context` to refresh this block.

## Running and verifying

- Follow `docs/setup.md`; run frontend commands from `frontend/`.
- Use `MODEL_RUNTIME=stub` for lightweight checks. H5 verification runs in Docker and requires a reviewed model contract before startup.

<!-- /bmad:context -->

# MDS01 Engineering Guide

This repository contains the FastAPI backend and a separate Next.js frontend.
Frontend visual work belongs under `frontend/`; backend changes must preserve
the API privacy boundaries described below.

## Architecture

The backend flow is:

```text
ZIP upload → FastAPI → PostgreSQL session → FastAPI BackgroundTasks
  → validation → de-identification → preprocessing
  → inference adapter → explanation artifact → PostgreSQL results
```

FastAPI routes must remain thin. Business logic belongs in services,
database access belongs in repositories, and long-running EEG work belongs in
`backend/app/services/processing_service.py` and is scheduled through FastAPI
BackgroundTasks.

## Privacy boundaries

- Keep EEG binaries outside PostgreSQL.
- Store files beneath `backend/storage/sessions/{session_id}/`.
- Never expose patient references, original metadata, filesystem paths, or
  original files through public API responses.
- Delete original and transient EEG files after processing; retain only the
  encrypted, transformed model-positive artifact allowed by the configured policy.
- Do not log patient-identifying values.
- Review EDF start dates and annotations before changing de-identification
  policy; they may contain sensitive timing information.
- Do not hard-code secrets or encryption keys.

## Processing contract

The reviewed model-input contract is 256 Hz, the exact 18 configured bipolar
channels, four-second windows with a two-second stride, and `(N, 1024, 18)`
`float32` input. The H5 runtime must validate the artifact hash and reviewed
contract at startup. An explicit deterministic fallback remains available:

```text
model_name: development-stub
model_version: stub-0.1.0
threshold: 0.5
```

Do not invent a real model architecture, output contract, preprocessing
parameters, or clinical explanation method.

## API

The primary API is asynchronous:

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
```

The old `/api/v1` prototype routes have been removed. New backend changes must
use only the asynchronous session and recording API described in the route list
above.

## Development rules

1. Inspect the existing code before creating a module.
2. Preserve working behavior and existing user changes.
3. Add tests for new validation, privacy, processing, and API behavior.
4. Use Alembic migrations; do not rely on production startup `create_all()`.
5. Use PostgreSQL in Docker Compose; schedule prototype processing with
   FastAPI BackgroundTasks.
6. Keep H5 inference behind the validated model contract and fail closed when
   the artifact, hash, runtime, or reviewed preprocessing contract is invalid.
7. Treat all outputs as research-only; label stub predictions as development data.
