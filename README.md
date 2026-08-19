# MDS01

This repository contains the backend and a separate frontend for MDS01, a
privacy-preserving EEG seizure-detection decision-support prototype.

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

- [Design system](DESIGN.md)
- [Apple design reference](apple/DESIGN.md)

## Frontend

The frontend is under [`frontend/`](frontend/). Start the backend with Docker,
then run the Next.js app separately:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`.
