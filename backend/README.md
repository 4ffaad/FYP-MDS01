# MDS01 backend

FastAPI backend for the MDS01 EEG research workflow. Routes stay thin;
services own processing, repositories own database access, and PostgreSQL
stores safe result metadata. Long-running prototype work runs through
FastAPI `BackgroundTasks`.

## Run

Run these commands from the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Use the deterministic development runtime when the reviewed H5 runtime is not
needed:

```bash
MODEL_RUNTIME=stub INSTALL_RESEARCH=false docker compose up --build
```

The API and OpenAPI UI are at <http://127.0.0.1:8000> and
<http://127.0.0.1:8000/docs>. Full setup instructions are in
[`docs/setup.md`](../docs/setup.md).

## Current API

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

The draft flow encrypts an EEG ZIP before privacy selection. Finalization
creates a session and queues background processing. The public API does not
return patient references, original filenames, filesystem paths, or source
files.

## EEG processing boundary

The reviewed model-input contract is 256 Hz, the configured 18 bipolar
channels, four-second windows with a two-second stride, and `(N, 1024, 18)`
`float32` input. The H5 adapter validates its artifact and contract at
startup. The explicit `development-stub` fallback is research data, not a
clinical prediction.

`metadata-scrub` is always applied. `signal-obfuscation` is an optional,
lossy research profile. Neither encryption nor signal transformation proves
anonymity. See [`docs/backend.md`](../docs/backend.md) and
[`docs/privacy-research.md`](../docs/privacy-research.md) for the full
processing and retention contracts.

## Tests

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=. .venv/bin/python -m compileall -q backend
```

Research-only evaluation and SHAP commands are documented in
[`docs/setup.md`](../docs/setup.md). Generated reports and model backgrounds
are ignored by Git.

## Video privacy status

Patient-video privacy is a separate planned subsystem. Its contract is
[`_bmad-output/specs/spec-patient-video-deidentification/SPEC.md`](../_bmad-output/specs/spec-patient-video-deidentification/SPEC.md).
It will use `video → privacy pipeline(s) → output` and will not invoke EEG,
H5, action analysis, or clinical inference. Do not place patient videos under
this repository; keep them in a private external directory.
