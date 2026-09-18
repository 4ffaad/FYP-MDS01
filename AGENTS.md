# MDS01 Engineering Guide

This repository contains the FastAPI backend and a separate Next.js frontend.
Frontend visual work belongs under `frontend/`; backend changes must preserve
the API privacy boundaries described below.

## Architecture

The backend flow is:

```text
EEG ZIP upload → FastAPI → PostgreSQL session → FastAPI BackgroundTasks
  → validation → de-identification → preprocessing
  → inference adapter → explanation artifact → PostgreSQL results

separate video upload → encryption → face redaction →
  Lightweight OpenPose keypoints → VSViG → encrypted predictions
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
- Video detection deletes the source and protected model-input video after
  processing; retain only its encrypted prediction artifact. The separate
  video-privacy utility has its own explicitly documented output policy.
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
parameters, or clinical explanation method. For video, use the pinned VSViG
and Lightweight OpenPose contract in `docs/video-detection.md`; do not replace
its source, checkpoints, or preprocessing silently.

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
POST /api/video-detection/jobs
GET  /api/video-detection/jobs
GET  /api/video-detection/jobs/{job_id}
GET  /api/video-detection/jobs/{job_id}/predictions
```

The old `/api/v1` prototype routes have been removed. EEG changes use the
asynchronous session and recording API; video detection remains an independent,
owner-filtered workflow.

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
