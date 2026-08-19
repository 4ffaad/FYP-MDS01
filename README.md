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

`control` removes EDF metadata. `cancellable-signal-projection` additionally
uses an ephemeral, keyed, lossy EEG transformation. The transformed windows,
not the untransformed windows, feed both seizure detection and the offline
identity attacker, so the utility/privacy trade-off can be measured honestly.
It is experimental risk reduction, not an anonymity guarantee. Uploaded
archives are AES-GCM encrypted while processing, then original, extracted,
de-identified, processed, and explanation files are removed. The public API
keeps only safe result metadata. A waveform preview is disabled by default and
may be enabled only for local development with `ENABLE_SIGNAL_PREVIEW=true`.

For the optional CHB-MIT research utilities, install
`backend/requirements-research.txt`. Verify an H5 model before enabling it;
the verifier writes an unreviewed contract that must be manually reviewed
before `MODEL_RUNTIME=h5` can start.

## What `.env.example` means

`.env.example` is a committed **template**, not a live configuration file and
not a source of secrets. Copy it to `.env`, replace its placeholders, and keep
that `.env` file private—it is ignored by Git. Docker Compose reads `.env`
automatically and passes the values to the backend. The two keys are required
because one encrypts uploaded archives and the other determines the research
signal transformation. Generate different values with `openssl rand -base64 32`.

## Documentation

- [Design system](DESIGN.md)
- [Beginner workflow and Mermaid diagrams](docs/workflow.md)

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
