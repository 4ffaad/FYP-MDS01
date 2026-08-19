# MDS01 backend

The backend accepts an EEG ZIP archive, creates a session, and schedules the
EEG pipeline with FastAPI `BackgroundTasks`. Each EDF passes through
validation, de-identification, preprocessing, development inference, and
explanation artifact generation.

## Local commands

From the repository root:

```bash
cp .env.example .env
# Set MDS01_STORAGE_KEY and MDS01_TEMPLATE_KEY to different `openssl rand -base64 32` values.
docker compose up --build
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Storage

The upload archive is AES-256-GCM encrypted while the job runs. Original,
extracted, de-identified, processed, and explanation files are
removed when processing ends; PostgreSQL retains only safe session metadata,
predictions, and explanation JSON. Set `ENABLE_SIGNAL_PREVIEW=true` only for a
local waveform demonstration.

## Privacy modes and research tools

- `control`: EDF header and free-text annotation scrubbing.
- `cancellable-signal-projection`: the same scrubbing plus an in-memory,
  keyed, lossy EEG transformation. Its transformed windows feed both the
  detector and the offline identity attacker for research-only comparison.

The endpoint stack does not need `requirements-research.txt`; it uses the
deterministic stub. The optional H5 runtime remains blocked until a compatible
artifact and manually reviewed model contract are supplied.

## Model status

The backend currently uses `development-stub` version `stub-0.1.0`. It creates
deterministic non-clinical predictions and explanations so the background
pipeline can be tested. The unintegrated model artifact is stored at
`backend/model/best_seizure_model.h5` and requires contract verification before
use.

## Project design

See the repository [design system](../DESIGN.md) for the shared interface and
privacy presentation rules.

For beginner-friendly instructions and Mermaid diagrams, see the [setup
guide](../docs/setup.md) and [backend internals](../docs/backend.md). The
frontend has its own [internal guide](../docs/frontend.md).
