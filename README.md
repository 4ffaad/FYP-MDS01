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
cp .env.example .env
# Replace both placeholders with different values from: openssl rand -base64 32
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

## Privacy research boundary

`metadata-scrub` removes EDF metadata while preserving waveform values.
`signal-obfuscation` additionally applies an ephemeral, keyed, lossy EEG
transformation before both seizure detection and offline privacy evaluation.
It is experimental risk reduction, not an anonymity guarantee. Uploaded
archives are AES-GCM encrypted while processing. Full originals and derived
files are deleted afterward; only encrypted artifacts around model-positive
windows may remain for private research review. The public API keeps only safe
result metadata and does not serve waveform data.

The endpoint stack uses the deterministic stub and does not need
`backend/requirements-research.txt`. The optional H5 runtime remains blocked
until a compatible artifact and manually reviewed model contract are supplied;
keep `MODEL_RUNTIME=stub` for endpoint testing.

## What `.env.example` means

`.env.example` is a committed **template**, not a live configuration file and
not a source of secrets. Copy it to `.env`, replace its placeholders, and keep
that `.env` file private—it is ignored by Git. Docker Compose reads `.env`
automatically and passes the values to the backend. The two keys are required
because one encrypts uploaded archives and the other determines the research
signal transformation. Generate different values with `openssl rand -base64 32`.

## Documentation

- [Design system](DESIGN.md)
- [Setup guide](docs/setup.md)
- [Backend internals](docs/backend.md)
- [Frontend internals](docs/frontend.md)
- [Privacy and model-score research note](docs/privacy-research.md)

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
