# Local setup and testing

## Requirements

- Git, Docker Desktop with Linux containers (or Docker Engine plus Compose v2 on Linux), and Node.js 22 or newer with npm.
- Run commands from the repository root unless a block changes directory.
- Use a local checkout; keep real patient EEG/video data outside it.
- No Python installation, AI editor, BMAD or downloaded agent skills are needed for the Docker-based demo.

The backend image uses Python 3.12 and `linux/amd64` for the bundled scientific/media dependencies. Docker Desktop can emulate it on Apple Silicon; the first build and H5 processing may be slow. Python dependencies are not yet fully locked, so retain build logs when comparing environments.

## First run

Start Docker, then:

```sh
node scripts/setup.mjs
docker compose up --build
```

The setup command creates `.env` and `frontend/.env.local` from safe templates.
It generates separate random storage/template keys and a database password. Existing files are never overwritten. Keep those files private; changing keys makes existing encrypted artifacts unreadable. Changing the database password does not update an already-initialized PostgreSQL volume.

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open [the interface](http://127.0.0.1:3000), [Swagger](http://127.0.0.1:8000/docs) or [health](http://127.0.0.1:8000/health).
These commands also work in PowerShell. On Linux, Docker may require your user to have access to its socket.

Both frontend and API bind to loopback. Each teammate runs their own database, files and keys. Do not share your `.env` or connect classmates to an unauthenticated network-facing instance.

## Runtime choices

| Mode | Configuration | What it tests |
| --- | --- | --- |
| Backend development stub (default) | Root `.env`: `MODEL_RUNTIME=stub`, `INSTALL_RESEARCH=false` | Real uploads, database, privacy pipeline and synthetic model scores |
| H5 research runtime | Root `.env`: `MODEL_RUNTIME=h5`, `INSTALL_RESEARCH=true` | Supplied H5 model under the reviewed contract |
| Browser-only stub | Frontend `.env.local`: `NEXT_PUBLIC_USE_API_STUB=true` | UI flows with synthetic browser data; no actual EEG/video processing |

After changing backend settings, run `docker compose up --build` again.
After changing frontend settings, restart `npm run dev` (or rebuild a production frontend).
An existing checkout retains its current mode; setup does not silently switch it.

H5 startup validates the model hash, input/output contract and reviewed status. A failure must be investigated; do not reshape data or mark a replacement artifact reviewed merely to get past startup.

With the research image built, verify the artifact:

```sh
docker compose run --rm --no-deps backend python backend/scripts/verify_h5_model.py backend/model/best_seizure_model.h5
```

The checked-in contract currently emits **uncalibrated scores**. Fitting and reviewing both privacy-profile calibrators is a separate research task. See [backend research tools](backend.md#profile-specific-calibration). Never present the development stub or an uncalibrated score as confidence.

## Try a patient-free EEG demo

Once the backend is running, generate a synthetic EDF ZIP inside the container and copy it out:

```sh
docker compose exec backend python -m backend.tests.generate_e2e_archive /tmp/mds01-demo.zip
docker compose cp backend:/tmp/mds01-demo.zip ./mds01-demo.zip
```

The generated archive contains synthetic signals and explicit test identifiers, not patient data. ZIP files are ignored by Git.

1. Open **EEG analysis → New EEG analysis** and choose `mds01-demo.zip`.
2. Select metadata scrub, optionally adding signal obfuscation.
3. Submit and wait for the session to finish.
4. Open a recording to review its timeline, threshold, flagged windows and model version.
5. Delete the completed session through the confirmation dialog when finished.

For video, use a short synthetic or appropriately consented MP4, MOV or WebM. Open **Video privacy**, select a profile, then review the transformed output. The browser stub does not validate the actual privacy transform. Docker builds smoke-test both video adapters as the unprivileged application user. Pose-only uses MediaPipe's bundled full model without a first-upload download. Face detection can miss frames; missing/failed transforms must not return source video.

## Enable waveform review for a local prototype

Both sides must opt in:

| File | Setting |
| --- | --- |
| Root `.env` | `ENABLE_SIGNAL_PREVIEW=true` |
| `frontend/.env.local` | `NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW=true` |

Restart both services and submit a new analysis. Only retained transformed data from model-positive recordings is available. Non-alert recordings have no waveform artifact.

For full transformed-recording preview, also set `ENABLE_FULL_SIGNAL_PREVIEW=true` in the backend and `NEXT_PUBLIC_ENABLE_FULL_SIGNAL_PREVIEW=true` in the frontend. This is a local-development exception, not a production privacy policy. Existing deleted data cannot be recovered by changing a flag.

## Tests

Setup safety check, from the repository root:

```sh
node --test scripts/setup.test.mjs
git diff --check
```

Backend unit tests require a separate local Python environment. Prefer Python 3.12 to match Docker:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m unittest discover -s backend/tests
```

PowerShell equivalents:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s backend/tests
```

Frontend checks, from `frontend/`:

```sh
npm ci
npx playwright install chromium
npm run lint
npx next typegen
npx tsc --noEmit
npm run build
npm run test:e2e
```

On a fresh Linux machine, use `npx playwright install --with-deps chromium` if browser system libraries are missing.
The desktop/mobile browser suite uses synthetic UI data on port 3001.

To test real Next.js → FastAPI → PostgreSQL behavior, first create the local Python environment above, then run from `frontend/`:

```sh
npm run test:e2e:real
```

This creates and removes only the disposable Compose project `mds01-security`, including its test volumes, on API port 18000 and frontend port 3002. Never store real data in that project. It exercises migrations, upload, background processing, safe results and deletion; it does not establish H5 accuracy or video anonymization.

## Stop, restart and troubleshoot

```sh
docker compose down
docker compose up
```

`down` preserves data. Do not add `-v` unless you intend to delete the project's database and private storage volumes.

| Problem | Check |
| --- | --- |
| Cannot connect to Docker | Start Docker Desktop; run `docker info`. |
| UI cannot reach API | Use `NEXT_PUBLIC_USE_API_STUB=false`, API URL `http://127.0.0.1:8000`, and check `docker compose ps`. |
| Backend exits | Run `docker compose logs backend`; check migrations, keys and selected runtime. Do not post secrets or patient data in logs. |
| H5 build is too slow | Use the backend development stub for workflow demos; H5/TensorFlow is optional. |
| Docker build hangs at image metadata | Check Docker Desktop's credential helper or Keychain prompt. This happens before application code is built; do not change application secrets to fix it. |
| Database authentication fails after editing config | An existing volume keeps its original password. Restore the matching local configuration; do not delete data to bypass the error. |
| Waveform returns 404 | Check both preview flags, positive windows, retention and whether the analysis was rerun after enabling preview. |
| Test browser missing | Run `npx playwright install chromium` in `frontend/`. |
| Port already allocated | Stop the conflicting local process, or update Compose port mapping, API URL and CORS together. |

Migrations run before FastAPI startup. Check the applied revision with:

```sh
docker compose exec backend alembic -c backend/alembic.ini current
```

Before network deployment, configure authenticated access, HTTPS and the remaining controls in [the security audit](security-audit.md). Local demonstration setup is not a deployment guide.
