# Local setup and testing

## Requirements

- Node.js 22 or newer, which includes npm.
- Run commands from the repository root unless a block changes directory.
- Use a local checkout; keep real patient EEG/video data outside it.

Choose either Docker or native mode:

| Mode | Install locally | Database | Best for |
| --- | --- | --- | --- |
| Docker | Docker Desktop plus Node.js | PostgreSQL container | Reproducible team setup and VSViG |
| Native | Python 3.12, FFmpeg plus Node.js | SQLite file | Fast single-laptop prototype work |

Neither mode requires an AI editor or agent skills. Native mode does require a
Python environment; Docker keeps those packages inside the image.

The backend image uses Python 3.12 and `linux/amd64` for the bundled scientific/media dependencies. Docker Desktop can emulate it on Apple Silicon; the first build and H5 processing may be slow. Python dependencies are not yet fully locked, so retain build logs when comparing environments.

Docker is the inference runtime, not merely a database wrapper. The VSViG and
Lightweight OpenPose Python code and dependencies run inside the backend
container. The large official checkpoints are deliberately supplied through a
named Docker volume initialized by `vsvig-assets-init`, instead of Git or the
application image. The backend mounts that volume read-only at `/opt/vsvig`.
On a remote Linux Docker host, initialize the volume on that host and point the
frontend at that API. The laptop then only opens the browser; it does not run
inference and does not provide a model path.
Docker still needs a machine somewhere with CPU/RAM and persistent encrypted
storage. It does not make model computation free or remove the need to protect
the model bundle.

## First run: Docker

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

The tracked `docker-compose.yml` includes the secure video runtime by default:
it builds the video image, runs `vsvig-assets-init` as a completed dependency,
verifies the named model volume, and starts the backend only after verification
succeeds. The browser upload still needs no absolute video path; the model
volume is an operator-managed Docker resource on the host. See [the video
runbook](video-detection.md) for the asset approval gate and remote-host details.

The default local mode is `local-accounts`. When `DEMO_ADMIN_PASSWORD` is
present, development mode seeds the demo administrator `admin@mds01.local`,
which can review all local records. `node scripts/setup.mjs` generates this
credential into the ignored `.env`; read it locally when you need the demo
login and never paste it into tickets, logs or chat.

The first browser visit shows the MDS01 sign-in page. For another teammate,
choose **Create an account** and use a non-patient email and a password of at
least 8 characters. The API stores only a salted password hash and an opaque
server-side session token. Sign out from the header when switching teammates.
The seeded administrator is intentionally development-only; production rejects
local authentication and requires Cloudflare Access.

Each authenticated account may keep at most two active EEG upload drafts and a
default of 2 GiB of pending encrypted draft storage. Drafts expire after
`UPLOAD_DRAFT_TTL_SECONDS` and are swept in the background even when no request
arrives. Adjust `MAX_UPLOAD_BYTES`, `MAX_ACTIVE_UPLOAD_DRAFTS` and
`MAX_PENDING_DRAFT_BYTES` only with a storage-capacity review.

## First run: native

From the repository root:

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

The native runner loads `.env` without printing it, defaults to SQLite and
local encrypted storage, applies migrations, and starts FastAPI on
`127.0.0.1:8000`. Set `PYTHON=/absolute/path/to/python` when the virtualenv is
not at `.venv`. Do not set `DATABASE_URL` if you want the SQLite default.

The native path is intentionally a single-process prototype profile. Keep the
Docker profile for the official VSViG runtime when PyTorch, pose weights, or
platform-specific wheels are not already verified on the host.

## Runtime choices

| Mode | Configuration | What it tests |
| --- | --- | --- |
| Backend development stub (default) | Root `.env`: `MODEL_RUNTIME=stub`, `INSTALL_RESEARCH=false` | Real uploads, database, privacy pipeline and synthetic model scores |
| H5 research runtime | Root `.env`: `MODEL_RUNTIME=h5`, `INSTALL_RESEARCH=true`, operator-populated `mds01-eeg-model-assets` volume | External H5 model under the reviewed contract |
| Local accounts (default) | Root `.env`: `AUTH_MODE=local-accounts` | Backend-enforced login and owner-filtered data |
| Unauthenticated backend test mode | Root `.env`: `AUTH_MODE=local` | API/service tests only; never expose this mode to a network |
| Browser-only stub | Frontend test config: `NEXT_PUBLIC_USE_API_STUB=true`, `NEXT_PUBLIC_AUTH_MODE=stub` | UI flows with synthetic browser data; no actual EEG/video processing |

After changing backend settings, restart the selected backend. Docker settings
require `docker compose up --build`; native settings require restarting
`node scripts/start-native.mjs`.
After changing frontend settings, restart `npm run dev` (or rebuild a production frontend).
An existing checkout retains its current mode; setup does not silently switch it.

H5 startup validates the model hash, input/output contract and reviewed status. A failure must be investigated; do not reshape data or mark a replacement artifact reviewed merely to get past startup.

Populate the named volume from an operator-controlled server directory before
selecting H5 mode. The browser and end users never provide this path:

```sh
docker run --rm \
  -v mds01-eeg-model-assets:/opt/eeg-model \
  -v "/absolute/private/eeg-model:/source:ro" \
  alpine:3.22 sh -c 'cp /source/best_seizure_model.h5 /source/model-contract.json /opt/eeg-model/'
```

With the research image built, verify the artifact:

```sh
docker compose run --rm --no-deps backend python backend/scripts/verify_h5_model.py /opt/eeg-model/best_seizure_model.h5
```

The mounted contract currently emits **uncalibrated scores**. Fitting and reviewing both privacy-profile calibrators is a separate research task. See [backend research tools](backend.md#profile-specific-calibration). Never present the development stub or an uncalibrated score as confidence.

## Try a patient-free EEG demo

Once the backend is running, generate a synthetic EDF ZIP inside the container and copy it out:

```sh
docker compose exec backend python -m backend.tests.generate_e2e_archive /tmp/mds01-demo.zip
docker compose cp backend:/tmp/mds01-demo.zip ./mds01-demo.zip
```

The generated archive contains synthetic signals and explicit test identifiers, not patient data. ZIP files are ignored by Git.

1. Open **Workspace → New analysis** and choose `mds01-demo.zip`.
2. Select metadata scrub, optionally adding signal obfuscation.
3. Submit and wait for the session to finish.
4. Open a recording to review its timeline, threshold, flagged windows and model version.
5. Delete the completed session through the confirmation dialog when finished.

For analysis, open **New analysis** and choose one EEG ZIP, one separate video, or both. EEG is encrypted and follows the selected EEG privacy path before H5 scoring. Video is encrypted, face-redacted, converted into one shared pose pass, and sent to the visual-only VSViG path; the same pose samples generate an encrypted audio-free, full-frame-blurred skeleton visualization for owner-only review. A paired upload opens one status page with links to the EEG session and video review. Detection excludes audio from model input and deletes source/protected work after processing, retaining only the encrypted results and privacy-safe visualization until expiry. The standalone **Video privacy** page also emits an audio-free protected transform. The browser stub does not validate the actual privacy transform. Docker builds smoke-test the installed video privacy dependencies as the unprivileged application user; the VSViG checkpoints are verified from the read-only named volume before startup. Face detection can miss frames; affected frames use full-frame blur and missing/failed transforms must not return source video.

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

Optional backend unit tests require a separate local Python environment. This
is not needed to run the application or the real browser workflow. Prefer
Python 3.12 to match Docker:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m unittest discover -s backend/tests
```

Native runner safety check:

```sh
node --test scripts/start-native.test.mjs
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
npm run format:check
npm run lint
npx next typegen
npx tsc --noEmit
npm run build
npm run test:e2e
```

On a fresh Linux machine, use `npx playwright install --with-deps chromium` if browser system libraries are missing.
The desktop/mobile browser suite uses synthetic UI data on port 3001.

To test real Next.js → FastAPI → PostgreSQL behavior, run from `frontend/`:

```sh
npm run test:e2e:real
```

This creates and removes only the disposable Compose project `mds01-security`, including its test volumes, on an available loopback API port and frontend port 3002. Set `MDS01_SECURITY_PORT` to use a specific API port. The synthetic EEG archive is generated inside the backend container, so this workflow needs only Docker and npm. Never store real data in that project. It exercises registration through the UI, the authenticated migration, upload, background processing, safe results and deletion; it does not establish H5 accuracy or video anonymization.

## Stop, restart and troubleshoot

```sh
docker compose down
docker compose up
```

`down` preserves data. Do not add `-v` unless you intend to delete the project's database and private storage volumes.

The automatic video overlay also means `docker compose down -v` deletes the
`mds01-vsvig-assets` model volume. Run `node scripts/setup.mjs` if needed, then
run `docker compose up --build` again; the completed initializer will rebuild
the volume before the backend starts.

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
## Video seizure detection

The normal one-command stack exposes the video review workspace. Real inference
requires the pinned VSViG and Lightweight OpenPose bundle; the initializer and
startup verifier run automatically before the backend. Follow the [video review
runbook](video-detection.md) for the named-volume approval gate, read-only
mount, input contract and failure meanings. Python is provided inside Docker.
The login account controls video-job ownership.
