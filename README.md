# SeizureAI

This repository currently contains the backend for a privacy-preserving EEG
processing application.

## Backend

The backend is under [`backend/`](backend/). It provides FastAPI routes,
PostgreSQL metadata storage, Redis/RQ background processing, session-scoped
file storage, EDF de-identification, preprocessing, and a deterministic
development inference stub.

Run the complete local stack with:

```bash
docker compose up --build
```

The API is available at `http://127.0.0.1:8000/docs`.

For unit tests without containers:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

The real seizure model has not been supplied. Stub results are explicitly
non-clinical and must not be used for medical decisions.
