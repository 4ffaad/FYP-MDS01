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
- Original files are retained per session under configurable retention policy.
- Do not log patient-identifying values.
- Review EDF start dates and annotations before changing de-identification
  policy; they may contain sensitive timing information.
- Do not hard-code secrets or encryption keys.

## Processing contract

The model-input contract is 256 Hz, the exact 18 configured bipolar channels,
four-second non-overlapping windows, and `(N, 1024, 18)` `float32` input.
These values must be verified against the real model before replacing the
development stub.

The current inference runtime is intentionally a deterministic,
non-clinical stub:

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
6. Keep the real model integration blocked behind an explicit adapter until
   the artifact and training-time preprocessing are supplied.
7. Treat stub predictions and explanations as non-clinical development data.
