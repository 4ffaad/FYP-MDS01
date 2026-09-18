# MDS01

A research prototype with one shared analysis entry point and one separate privacy utility:

- **Unified analysis:** open **New analysis** and upload one EEG archive, one separate video, or both. EEG follows `privacy → H5 model → report`; video follows `full-frame privacy blur → pose keypoints → VSViG model → visual evidence review`. A paired upload has one status page with links to both modality reviews.
- **Video privacy:** upload a video, apply face redaction, then review/download an encrypted protected output. Original audio is retained for owner-only review and may contain identifying speech. Video never enters the EEG model.
- **Video detection:** authenticated full-frame-blurred Lightweight OpenPose + VSViG review with a shared pose pass, privacy-safe protected playback, window scores, flagged intervals, and bounded model-input sensitivity. The default Docker command initializes and verifies the named model volume; the service fails closed if its reviewed contract is unavailable.

Model output is **not a diagnosis**. Privacy transforms do not guarantee anonymity.

## Start on your laptop

Choose one backend profile. Docker is the reproducible team path; native mode is the lighter single-laptop prototype path.

### Docker

Only **Docker Desktop** (Linux containers) and **Node.js 22 or newer** (with npm) are required. Start Docker and run from the repository root:

```sh
node scripts/setup.mjs
docker compose up --build
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open [MDS01](http://127.0.0.1:3000) or [API documentation](http://127.0.0.1:8000/docs).
The setup command generates local secrets and leaves existing configuration untouched. Python and backend package installation are handled inside Docker.
New installations use the deterministic **development stub**; existing `.env` runtime choices are preserved.
New installations also use `AUTH_MODE=local-accounts`: register the first
teammate in the browser, then sign in. Ordinary accounts see only their own EEG
sessions, upload drafts and video jobs; the development-only demo administrator
has read-only cross-owner review access. Use `AUTH_MODE=local` only for explicit
unauthenticated backend tests.
For H5 scores, waveform preview, sample data, Windows instructions and troubleshooting, see [setup](docs/setup.md).
For the official VSViG/pose bundle, video input contract, privacy lifecycle and
presentation checklist, see [video detection](docs/video-detection.md).

### Native prototype (no Docker)

Install Python 3.12, Node.js 22+, and FFmpeg. From the repository root:

```sh
node scripts/setup.mjs
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
node scripts/start-native.mjs
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Native mode uses SQLite at `backend/database/eeg.db` and encrypted files under
`backend/storage/`. It is intended for one laptop and low-volume prototype
work. The VSViG model dependencies are platform-sensitive; use the default
Docker Compose runtime for the real VSViG path unless your host installation
has been independently verified. The native runner automatically applies `.env`, runs Alembic,
and starts FastAPI with reload.

## How it fits together

```mermaid
flowchart LR
    Browser[Next.js interface] --> Auth[Login or register]
    Auth --> Cookie[HttpOnly session cookie]
    Cookie --> API[FastAPI auth dependency]
    API --> DB[(SQLite native / PostgreSQL Docker)]
    API --> Workspace[Unified analysis workspace]
    Workspace --> EEG[EEG processing]
    API --> Video[Video privacy processing]
    API --> Detection[Video review: encryption + face redaction]
    Detection --> Pose[Lightweight OpenPose keypoints]
    Pose --> VSViG[VSViG score + evidence timeline]
    VSViG --> Files
    EEG --> Model[H5 adapter or development stub]
    Model --> DB
    EEG --> Files[(Private encrypted storage)]
    Video --> Files
    API --> Owner[Owner-filtered EEG and video queries]
```

| Location | Responsibility |
| --- | --- |
| `frontend/src/app/` | Routes and shared layout |
| `frontend/src/components/` | Screens, waveform/timeline views, UI primitives |
| `frontend/src/lib/` | API adapter, view-model types, formatting |
| `backend/app/api/` | HTTP validation and responses |
| `backend/app/services/` | Upload, processing, storage and cleanup |
| `backend/app/eeg/`, `privacy/`, `ml/` | Model inputs, privacy transforms, inference |
| `backend/app/video_privacy/` | Standalone video transforms |
| `backend/app/video_detection/` | Validated VSViG/pose assets, preprocessing and inference |
| `backend/app/database/`, `backend/migrations/` | Persistence and schema history |
| `backend/app/research/`, `backend/scripts/` | Offline evaluation and calibration |
| `scripts/` | Local setup and its safety test |

## Documentation

Use the [documentation map](docs/README.md) to find the one guide relevant to
your task. It separates runnable setup and architecture from supporting
research and security records. The operator-mounted H5 contract currently has
no active calibrators; the EEG confidence document is background, not a
performance claim.

## Repository hygiene

Commit source, tests, migrations and the frontend package lock. Keep `.env`, patient data, ZIP/RAR uploads, encrypted storage, generated reports, model weights/contracts and model backgrounds local-only. Store real patient data **outside the repository**.

`.dockerignore` limits builds to backend source; the H5 and VSViG bundles are
operator-managed named volumes mounted read-only at runtime. `.gitignore`
excludes common private artifacts. Neither
replaces checking files before a commit. Agent skills under `.agents/` are
optional developer tooling; teammates do not need an AI editor or BMAD to run
this project.
