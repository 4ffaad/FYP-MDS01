# Local setup and testing

## Requirements

- Node.js 22 or newer, which includes npm.
- Run commands from the repository root unless a block changes directory.
- Use a local checkout; keep real patient EEG/video data outside it.

Choose either Docker or native mode:

| Mode   | Install locally                  | Database             | Best for                          |
| ------ | -------------------------------- | -------------------- | --------------------------------- |
| Docker | Docker Desktop plus Node.js      | PostgreSQL container | Reproducible team setup and VSViG |
| Native | Python 3.12, FFmpeg plus Node.js | SQLite file          | Fast single-laptop prototype work |

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

Start Docker. From the repository root, run the complete local H5 demo:

```sh
node scripts/demo.mjs
```

The launcher creates or safely repairs `.env` and
`frontend/.env.local` without
printing their values. It preserves nonempty settings, generates separate
random storage/template keys and a database password when needed, and requests
`0600` permissions where POSIX file modes apply. On Windows, protect the files
with your normal user-profile permissions. Keep them private; changing keys
makes existing encrypted artifacts unreadable. Changing the database
password does not update an already-initialized PostgreSQL volume.

It installs the locked frontend dependencies when needed, starts PostgreSQL,
the H5 research runtime, private storage, and verified VSViG assets, then starts
Next.js on port 3000. Press Ctrl-C to stop the frontend; Docker services and
their data remain running.

The backend validates the exact H5 artifact and contract at startup; missing or
mismatched files fail closed. The first image/model-asset initialization needs
internet access and may take longer than later starts. If startup fails, check
the launcher and Docker output; do not copy local secrets into chat or logs.

Open [the interface](http://127.0.0.1:3000), [Swagger](http://127.0.0.1:8000/docs) or [health](http://127.0.0.1:8000/health).
These commands also work in PowerShell. On Linux, Docker may require your user to have access to its socket.

`docker compose down` stops the containers while keeping
database and encrypted-storage volumes. Do not use `docker compose down -v`
unless you intentionally want to delete those volumes.

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

| Mode                              | Configuration                                                                       | What it tests                                                        |
| --------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Local H5 research/demo profile    | `node scripts/demo.mjs`                                                             | Exact ignored local candidate, pinned contract hash, read-only mount |
| Backend development stub          | `node scripts/demo.mjs --development-stub`                                          | Real uploads, database, privacy pipeline and synthetic model scores  |
| Local accounts (default)          | Root `.env`: `AUTH_MODE=local-accounts`                                             | Backend-enforced login and owner-filtered data                       |
| Unauthenticated backend test mode | Root `.env`: `AUTH_MODE=local`                                                      | API/service tests only; never expose this mode to a network          |
| Browser-only stub                 | Frontend test config: `NEXT_PUBLIC_USE_API_STUB=true`, `NEXT_PUBLIC_AUTH_MODE=stub` | UI flows with synthetic browser data; no actual EEG/video processing |

After changing backend settings, restart the selected backend. Docker settings
require `docker compose up --build`; native settings require restarting
`node scripts/start-native.mjs`.
After changing frontend settings, restart `node scripts/demo.mjs` for the
one-command demo, or restart `npm run dev` when running the frontend separately.
Setup preserves nonempty user secrets and explicit Compose selections. New configs
select the H5 research overlay because the template explicitly sets
`MODEL_RUNTIME=h5`; older configs without a Compose selection also default to H5
when their runtime is absent or `h5`. If an existing config explicitly sets
`MODEL_RUNTIME=stub` but has no Compose selection, setup adds only
`docker-compose.yml` and leaves `COMPOSE_PROFILES` empty, so it stays on the stub.
Pass `-f docker-compose.yml` to explicitly use the stub-only base file.
Nonempty Compose selections are preserved; if an explicit selection activates
the local-research overlay, that overlay sets the effective runtime to H5 even
if `MODEL_RUNTIME` says `stub`.

H5 startup validates the model hash, input/output contract and reviewed status. A failure must be investigated; do not reshape data or mark a replacement artifact reviewed merely to get past startup.

The local H5 overlay requires the exact
`backend/model/best_seizure_model.h5` and `backend/model/model-contract.json`
files. It pins the reviewed contract hash and bind-mounts both files read-only.
The backend verifies the artifact hash, tensor contract, output activation, and
local research runtime at startup. Missing or mismatched assets fail closed. H5
output is uncalibrated, non-diagnostic, and not a probability or clinical
validation result.

For the one-patient folder flow, open [the `/upload` route](http://127.0.0.1:3000/upload) (**New patient review**) and select a patient folder. This screen accepts a folder, not an EEG ZIP. The local report draft and human-review gate, strict video preflight, pairing rules, encrypted approved identity fields, and remaining constraints are documented in [one-patient research/demo](one-patient-research-demo.md).

The H5 candidate is not copied into a Docker named volume by hand. The local
research profile mounts only the two expected files read-only. Its scores are
uncalibrated and are never confidence/probability estimates. Fitting
privacy-profile calibrators is a separate research task; see
[backend research tools](backend.md#profile-specific-calibration).

## Try a patient-free one-patient-folder demo

The current `/upload` route accepts a folder, not an EEG ZIP. With the Docker
backend running, generate a synthetic EDF and report folder inside the backend
container, then copy the folder to the repository root:

```sh
docker compose exec backend python backend/tests/generate_e2e_archive.py --synthetic-veeg-folder /tmp/mds01-demo-patient
docker compose cp backend:/tmp/mds01-demo-patient ./mds01-demo-patient
```

The generated folder contains a synthetic EDF and a minimal `.docx` with the
`SYNTHETIC_VEEG_STUDY` test summary. EDF metadata values are synthetic test
markers, not patient data.

1. Open `http://127.0.0.1:3000/upload` (**New patient review**) and select
   `mds01-demo-patient`.
2. Keep the EEG file selected; report details are unchecked by default. Opt in
   only to details you explicitly want added to the case profile.
3. Choose **Create patient review**, then wait for the session to finish.
4. Open the case to review its status and results.
5. Delete the completed session when finished.

For video association, follow [the workflow guide](one-patient-research-demo.md).
Native 1920×1080 video is the default VSViG input. The local H5 profile enables
experimental aspect-preserving resizing for smaller sources, filling the
remaining area with black padding when needed. It adds no captured detail and
is not validated as equivalent to native input. The separate **Video privacy** utility
has its own documented transform policy. The browser stub does not validate the
actual privacy transform. Docker builds smoke-test the installed video privacy
dependencies as the unprivileged application user; the VSViG checkpoints are
verified from the read-only named volume before startup. Missing or failed
transforms must not return source video.

The API encrypts EEG and video uploads before writing them to private storage;
PostgreSQL stores metadata, not media files. The browser and API bind to
`127.0.0.1`, so the local upload stays on the same machine. That local HTTP
connection is not TLS-encrypted. Do not expose the ports to another device; a
network-hosted deployment needs HTTPS at its reverse proxy.

## Enable waveform review for a local prototype

Both sides must opt in:

| File                  | Setting                                  |
| --------------------- | ---------------------------------------- |
| Root `.env`           | `ENABLE_SIGNAL_PREVIEW=true`             |
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

| Problem                                            | Check                                                                                                                                                    |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cannot connect to Docker                           | Start Docker Desktop; run `docker info`.                                                                                                                 |
| UI cannot reach API                                | Use `NEXT_PUBLIC_USE_API_STUB=false`, API URL `http://127.0.0.1:8000`, and check `docker compose ps`.                                                    |
| Backend exits                                      | Run `docker compose logs backend`; check migrations, keys and selected runtime. Do not post secrets or patient data in logs.                             |
| H5 build is too slow                               | Use the backend development stub for workflow demos; H5/TensorFlow is optional.                                                                          |
| Docker build hangs at image metadata               | Check Docker Desktop's credential helper or Keychain prompt. This happens before application code is built; do not change application secrets to fix it. |
| Database authentication fails after editing config | An existing volume keeps its original password. Restore the matching local configuration; do not delete data to bypass the error.                        |
| Waveform returns 404                               | Check both preview flags, positive windows, retention and whether the analysis was rerun after enabling preview.                                         |
| Test browser missing                               | Run `npx playwright install chromium` in `frontend/`.                                                                                                    |
| Port already allocated                             | Stop the conflicting local process, or update Compose port mapping, API URL and CORS together.                                                           |

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
