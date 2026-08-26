# MDS01 project handoff

MDS01 — EEG Research Review is a research-only, non-clinical EEG processing
and model-result review prototype. The
frontend is a Next.js clinician interface; the backend is FastAPI with
PostgreSQL, Alembic, private encrypted storage, and in-process
`BackgroundTasks`.

## Current data flow

```mermaid
flowchart LR
    Upload[ZIP upload] --> Stage[AES-GCM encrypted draft]
    Stage --> Privacy[Required metadata scrub]
    Privacy --> Optional{Optional signal obfuscation?}
    Optional -->|No| Tensor[(N, 1024, 18) float32]
    Optional -->|Yes| Transformed[Shape-preserving transformed tensor]
    Transformed --> Tensor
    Tensor --> Model[Reviewed H5 model or explicit development stub]
    Model --> Predictions[Window prediction rows]
    Predictions --> Alerts[Merge seizure_detected windows]
    Alerts --> Results[Safe session and recording results]
    Alerts --> Retention[Retain only positive clips + up to 10 min context]
```

One uploaded ZIP creates one session. EDF recordings remain grouped beneath
that session. Processing is per recording, so one malformed EDF does not stop
its siblings.

## Privacy contract

Encrypted storage and metadata protection are always enabled. The upload
configuration sends one of these ordered profiles:

```json
["metadata-scrub"]
```

```json
["metadata-scrub", "signal-obfuscation"]
```

The first is the required baseline. The second applies the keyed, lossy
signal transformation before inference. “No additional transformation” means
the first profile only; it does not disable encryption or metadata scrubbing.
The synthetic before/after preview appears only during upload configuration.

Signal obfuscation is experimental risk reduction, not formal anonymization.
The deterministic development stub is not a medical model and its score is
not confidence, accuracy, or a whole-recording probability.

## Alert truth

The dashboard and result pages use only persisted prediction rows:

```text
model alert = at least one prediction.seizure_detected == true
```

Optional `.edf.seizures` sidecars are internal research labels only. They do
not create, remove, count, color, retain, or display alerts. Positive windows
are merged into recording-relative intervals such as `12:04–12:16`, and the
complete score timeline runs from the start to the end of the recording.

For the development stub, use amber wording: `Development flag` and
`Development score`. Red model-alert wording is reserved for a reviewed,
calibrated real model.

## Frontend reading order

1. `frontend/src/components/AppShell.tsx` — shared navigation and privacy boundary.
2. `frontend/src/components/UploadScreen.tsx` — stage the ZIP, select the profile, and submit.
3. `frontend/src/components/PrivacyPreview.tsx` — synthetic 18-channel before/after preview.
4. `frontend/src/components/DashboardScreen.tsx` — session grouping and polling.
5. `frontend/src/components/SessionDetailScreen.tsx` — processing progress and alert times.
6. `frontend/src/components/SessionRecordings.tsx` — alert-first recording filters and deletion dialog.
7. `frontend/src/components/ResultScreen.tsx` — headline, alert intervals, complete score timeline, and technical details.
8. `frontend/src/components/SignalViewer.tsx` — bounded retained positive waveform only.
9. `frontend/src/lib/api.ts` and `frontend/src/lib/types.ts` — API adapter and view-model contracts.

## Backend reading order

1. `backend/app/main.py` — application startup and routers.
2. `backend/app/api/uploads.py` and `backend/app/api/sessions.py` — staging, finalization, and session routes.
3. `backend/app/services/processing_service.py` — linear per-recording pipeline.
4. `backend/app/privacy/methods.py` — canonical profile parsing.
5. `backend/app/privacy/retention.py` — alert merging and positive-only retention.
6. `backend/app/eeg/model_input.py` and `backend/app/eeg/preprocessing.py` — model contract.
7. `backend/app/ml/` — deterministic stub and reviewed-model gate.
8. `backend/app/database/models/eeg.py` and `backend/app/database/repository.py` — persistence.
9. `backend/migrations/versions/` — schema history.

## Local verification

```bash
docker compose up --build
cd frontend && npm run dev
```

The frontend is at `http://127.0.0.1:3000`; Swagger is at
`http://127.0.0.1:8000/docs`. Docker defaults to H5 and fails closed until the
model contract is independently reviewed. Use
`MODEL_RUNTIME=stub docker compose up --build` for fast non-clinical tests.

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend && npm run lint && npm run build && npm run test:e2e
```

## Pitch points

- The team adapted a linear, milestone-based workflow around a working vertical slice: upload, privacy configuration, asynchronous processing, and safe review.
- Progress is tracked through session status, per-recording processing counts, processing-attempt rows, tests, and the project documentation.
- Current development issues are model-contract verification, processing time for long EDF archives, and distinguishing development scores from clinical evidence.
- Main risks are EEG biometric leakage, model miscalibration, and interrupted in-process background work; each is bounded or documented rather than hidden.
- End-user validation focuses on whether a clinician can identify the session, exact model-alert intervals, privacy treatment, and the non-clinical status of the output without seeing private identifiers.
- Accuracy claims are reserved for the patient-disjoint CHB-MIT evaluator. Live uploads show threshold crossings and timestamps, while optional H5 SHAP output is labelled research attribution rather than clinical reasoning.
