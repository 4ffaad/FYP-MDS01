# Run MDS01 locally

## What you need

- Docker Desktop running with Linux containers.
- Node.js 22 or newer.
- Internet access for the first image and video-model asset setup.
- A local EEG H5 model and its reviewed contract only if you want real H5 EEG
  inference. Keep both files out of Git.

The project is a research prototype. Use only data approved for this workflow.
The current API grants access to the uploading account only; it does not
implement multi-user clinician roles, case sharing, or consent management. The
local HUKM demo enables owner-only unblurred video review; clean environments
default the access switch off.

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

The default demo selects the real H5 EEG research profile and requires these
local files:

```text
backend/model/best_seizure_model.h5
backend/model/model-contract.json
```

The backend checks the model hash and reviewed contract at startup. Missing or
mismatched files stop startup; there is no automatic fallback to synthetic
scores. Do not change the contract just to bypass that check.

To use synthetic EEG scores for a workflow-only development demo, explicitly
run:

```sh
node scripts/demo.mjs --development-stub
```

The stub is useful for demonstrating upload and review screens. Its scores do
not come from seizure detection or the H5 model.

Unblurred reference video review is controlled by
`MDS01_CLINICAL_VIDEO_REVIEW_ENABLED`. Generated local setup enables owner-only
playback for the demo. A backend started without this setting defaults to
disabled. Combined VEEG intake encrypts and retains the original, then returns
without waiting for media probing or conversion. Compatible H.264 MP4 with
optional AAC audio plays directly. Unsupported formats are prepared as an
encrypted, browser-playable copy only after the owner opens that clip's popup.
This is format conversion only; it does not run OpenPose or VSViG. The setting
controls reference-media access and does not add shared clinician roles.

On first visit, create a local account or sign in. EEG/video synchronization
is available only when a supported Nicolet `.e` recording and a complete
selected video folder produce one unique metadata match. Arbitrary matching by
filename or upload time is not used, and a unique metadata match does not prove
original-file identity.

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

The configured storage key must remain outside Git and outside ordinary data
backups. Backups must protect both ciphertext and key material independently,
with a tested recovery and key-rotation procedure; this repository does not
configure that production service. AES-GCM protects retained file contents and
detects ciphertext tampering, but a lost or replaced key can make files
unreadable. Do not rotate a key against a populated storage volume without a
verified re-encryption and restore plan.

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
| H5 model is missing | The default workflow requires the two local files above. Keep their reviewed contract unchanged; use `--development-stub` only for a synthetic workflow demo. |
| Video model assets are missing | Restart with node scripts/demo.mjs; the Compose initializer downloads and verifies the pinned bundle. |
| Video reports incomplete_pose | A scored window needs the 15 VSViG-selected pose points. Other OpenPose joints are not required; incomplete person windows remain unscored. |
| A port is busy | Stop the conflicting process or change the Compose port and matching frontend API/CORS settings together. |
