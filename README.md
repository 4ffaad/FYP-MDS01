# SeizureAI

This repository currently contains the backend for a privacy-preserving EEG
processing application.

## Backend

The backend is under [`backend/`](backend/). It provides FastAPI routes,
PostgreSQL metadata storage, FastAPI BackgroundTasks processing,
session-scoped file storage, EDF de-identification, preprocessing, and a
deterministic development inference stub.

Run the complete local stack with:

```bash
docker compose up --build
```

The API is available at `http://127.0.0.1:8000/docs`.

For unit tests without containers:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

An unintegrated model artifact is stored at
`backend/model/best_seizure_model.h5`. The backend still uses its deterministic
development stub until the artifact's runtime and training contract are
verified. Stub results are explicitly non-clinical and must not be used for
medical decisions.

## Documentation

- [Architecture](docs/architecture.md)
- [Local setup](docs/setup.md)
- [API reference](docs/api.md)
- [EEG pipeline](docs/pipeline.md)
- [Database](docs/database.md)
- [Storage and privacy](docs/storage-and-privacy.md)
- [Code map](docs/code-map.md)
- [Troubleshooting](docs/troubleshooting.md)
