# Run MDS01 locally

## What you need

- Docker Desktop running with Linux containers.
- Node.js 22 or newer.
- Internet access for the first image and video-model asset setup.
- A local EEG H5 model and its reviewed contract only if you want real H5 EEG
  inference. Keep both files out of Git.

The project is a research prototype. Use only data approved for this workflow.

## Start the local app

From the repository root:

```sh
node scripts/demo.mjs
```

This prepares ignored local configuration, builds/starts Docker services, and
runs the browser app at [http://127.0.0.1:3000](http://127.0.0.1:3000). The API
docs appear at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
First startup can take a while as Docker downloads dependencies and initializes
the pinned video-model volume.

The default demo selects the local H5 EEG profile. It requires these local
files:

```text
backend/model/best_seizure_model.h5
backend/model/model-contract.json
```

The backend checks the model hash and reviewed contract at startup. Missing or
mismatched files stop H5 inference; do not change the contract just to bypass
that check.

To use synthetic EEG scores instead:

```sh
node scripts/demo.mjs --development-stub
```

The stub is useful for demonstrating upload and review screens. Its scores do
not come from seizure detection.

On first visit, create a local account or sign in. The app does not infer an
EEG/video match from filenames or claim that their clocks are synchronized.

## Use a synthetic patient-folder demo

To create a test folder without using real recordings:

```sh
docker compose exec backend python backend/tests/generate_e2e_archive.py --synthetic-veeg-folder /tmp/mds01-demo-patient
docker compose cp backend:/tmp/mds01-demo-patient ./mds01-demo-patient
```

Then open **New patient review** and select **mds01-demo-patient**. It contains
synthetic data for workflow testing. Delete it when finished. To try a real
video, follow the input limits and failure meanings in the
[video runbook](video-detection.md).

## Data and stop/restart

PostgreSQL stores application records and results. EEG/video bytes stay outside
the database in encrypted private storage. The Compose volumes persist when
containers stop.

```sh
docker compose down
```

This stops the services and keeps their data. The command **docker compose down
-v** deletes the database, encrypted files, and downloaded video-model volume;
use it only when intentionally resetting the local project.

The app binds to loopback for local use. Do not expose these ports to another
device or the internet. Network deployment needs a separate security review,
HTTPS, and production authentication.

## Checks

Backend tests, from the repository root:

```sh
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

Frontend checks, from frontend/:

```sh
npm ci
npm run format:check
npm run lint
npx next typegen
npx tsc --noEmit
npm run build
npm run test:e2e
```

The browser suite uses synthetic UI data. For authenticated Next.js → FastAPI →
PostgreSQL integration, run **npm run test:e2e:real** from frontend/; it uses a
disposable test stack and synthetic inputs. These checks do not establish
model accuracy or video anonymity.

For launcher checks, run **node --test scripts/setup.test.mjs** and
**node --test scripts/start-native.test.mjs**. A native SQLite mode exists, but
Docker is the documented local runtime.

## Common problems

| Problem | Check |
| --- | --- |
| Docker is unavailable | Start Docker Desktop and run docker info. |
| Backend exits | Run docker compose ps and docker compose logs backend. Never share secrets or patient data from logs. |
| H5 model is missing | Check the two local files listed above; keep their reviewed contract unchanged. |
| Video model assets are missing | Restart with node scripts/demo.mjs; the Compose initializer downloads and verifies the pinned bundle. |
| Video reports incomplete_pose | The clip did not pass the full-pose gate, so VSViG did not produce a score. Use one clearly visible person with adequate framing and lighting. |
| A port is busy | Stop the conflicting process or change the Compose port and matching frontend API/CORS settings together. |
