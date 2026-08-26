# MDS01

MDS01 is a research-only EEG review application. It has a FastAPI/PostgreSQL
backend and a separate Next.js frontend. The current implemented product is
the asynchronous EEG upload, privacy, preprocessing, inference, and result
review flow. It must not be presented as a clinical diagnostic system.

The implemented standalone patient-video privacy surface is:

```text
video upload → selected privacy pipeline(s) → encrypted output → cleanup
```

It is intentionally separate from EEG/H5 inference. Choose `Face redaction`
or `Pose-only` at `/video-privacy`; the backend retains only encrypted
transformed output and a representative transformed frame. Video files and
patient datasets stay outside this repository.

## Repository layout

```text
backend/       FastAPI application, migrations, services, and tests
frontend/      Next.js application and browser tests
docs/          Setup, architecture, privacy, security, and handoff notes
_bmad/         Checked-in BMad configuration and workflow scripts
.agents/       Installed BMad skills used by this repository
_bmad-output/  BMad planning artifacts and feature specifications
```

The backend keeps routes thin, services responsible for processing, and
repositories responsible for database access. Private session files are
encrypted and stored under `backend/storage/` during local development.

## Run locally

From the repository root:

```bash
cp .env.example .env
openssl rand -base64 32
openssl rand -base64 32
```

Put the two generated values into `.env` as different values for
`MDS01_STORAGE_KEY` and `MDS01_TEMPLATE_KEY`. Then start the backend stack:

```bash
docker compose up --build
```

The API and Swagger UI are available at <http://127.0.0.1:8000> and
<http://127.0.0.1:8000/docs>.

For the fast deterministic development runtime:

```bash
MODEL_RUNTIME=stub INSTALL_RESEARCH=false docker compose up --build
```

Run the frontend separately:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The frontend is available at <http://127.0.0.1:3000>.

## Verify the repository

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=. .venv/bin/python -m compileall -q backend
cd frontend && npm run lint && npm run build && npm run test:e2e
```

The H5 runtime is review-gated and its scores are uncalibrated research
scores. Use the development stub for ordinary local testing unless the model
contract and research dependencies have been reviewed.

Video privacy processing uses OpenCV for face redaction and MediaPipe for
pose-only rendering. Both outputs are audio-free and metadata-scrubbed. A
missing runtime fails closed; it never returns an untransformed video.

## Privacy and data hygiene

- Never commit `.env`, frontend `.env.local`, patient videos, EEG datasets,
  private keys, model background tensors, generated reports, or storage files.
- Keep patient data in a private directory outside the repository, such as
  `/Users/daffa/PrivatePatientData/`.
- The checked-in `.env.example` files contain placeholders only; they are setup
  templates, not credentials.
- Public API responses must not expose patient references, original metadata,
  original filenames, filesystem paths, hashes, or source files.
- Encryption protects storage; it does not make EEG or video data anonymous.
- Video privacy jobs use generated labels and the `VID-…` identifier; original
  filenames and paths are not returned by the API.

See [`docs/setup.md`](docs/setup.md), [`docs/repository-handoff.md`](docs/repository-handoff.md),
[`docs/security-audit.md`](docs/security-audit.md), and
[`docs/privacy-research.md`](docs/privacy-research.md) before handling real
data.

## BMad workflow

BMad is part of the repository handoff. Use its skills through the agent/chat
interface—for example, `bmad-help`, `bmad-project-context`, `bmad-architecture`,
or `bmad-build`; they are not shell commands. Project instructions live in
[`AGENTS.md`](AGENTS.md). Planning artifacts are under `_bmad-output/`.

The recommended order for a new feature is:

1. clarify the intent with `bmad-help`;
2. lock the requirements in a spec;
3. ratify architecture and stories when the feature is ready;
4. implement with `bmad-build`; and
5. review the resulting diff before handoff.
