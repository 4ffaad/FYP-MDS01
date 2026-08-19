# MDS01 backend

The backend accepts an EEG ZIP archive, creates a session, and schedules the
EEG pipeline with FastAPI `BackgroundTasks`. Each EDF passes through
validation, de-identification, preprocessing, development inference, and
explanation artifact generation.

## Local commands

From the repository root:

```bash
docker compose up --build
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Storage

Runtime files are written to `backend/storage/sessions/{session_id}/` and are
ignored by Git. PostgreSQL stores metadata and result references only.

## Model status

The backend currently uses `development-stub` version `stub-0.1.0`. It creates
deterministic non-clinical predictions and explanations so the background
pipeline can be tested. The unintegrated model artifact is stored at
`backend/model/best_seizure_model.h5` and requires contract verification before
use.

## Project design

See the repository [design system](../DESIGN.md) for the shared interface and
privacy presentation rules.
