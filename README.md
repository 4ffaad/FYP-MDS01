# MDS01 — EEG/VEEG review prototype

MDS01 is a local research prototype built with a Next.js web app, FastAPI backend, and PostgreSQL. It reviews EEG recordings, matches available video to EEG time, and runs a separate experimental VSViG video analysis. Model results support review; they do not diagnose seizures.

This README is the laptop setup and handover starting point. Read only the linked guides when you need more detail.

## What the app does

- **EEG review:** displays source EEG and H5 model-flagged windows.
- **VEEG review:** lets the owner open an attached video beside EEG. Verified clips follow EEG time; unmatched clips can still be viewed without claiming synchronization. This does not run OpenPose or VSViG.
- **Video analysis:** a separate workflow that runs pose extraction, VSViG, and supported Grad-CAM output on a standalone clip.

## Set it up on a laptop

### 1. Install the prerequisites

- Git
- Docker Desktop, running with Linux containers
- Node.js 22 or newer
- Internet access for the first Docker build and pinned video-model download

### 2. Get the project

Use a GitHub account with access to the repository:

```sh
git clone https://github.com/4ffaad/FYP-MDS01.git
cd FYP-MDS01
```

### 3. Add the EEG model files

The reviewed H5 model files are intentionally not in Git. Get the **approved copies** from the team’s secure handover location and place them here:

```text
backend/model/best_seizure_model.h5
backend/model/model-contract.json
```

Keep these files unchanged. The normal demo checks that they match the reviewed model contract and stops if they are missing or invalid. Do not substitute a similarly named model.

The pinned VSViG and pose assets are downloaded and verified by Docker on first start. They are kept in a Docker volume, outside the repository; you do not need to copy them manually.

### 4. Start the demo

From the repository root:

```sh
node scripts/demo.mjs
```

The launcher prepares local settings, builds and starts PostgreSQL and FastAPI, applies database migrations, waits for the backend, then starts Next.js. It installs the locked frontend packages if they are missing. First startup takes longer because Docker builds the image and downloads the pinned video assets.

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), then create a local account or sign in. The FastAPI reference is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

For a synthetic UI walkthrough only, you can run `node scripts/demo.mjs --development-stub`. That mode does **not** run the H5 EEG model and its EEG scores are synthetic.

### What is `.env.example`?

You normally do not edit it. It is a safe template read by `scripts/setup.mjs`. The launcher copies it to the ignored local `.env`, generates local passwords and encryption keys, and creates `frontend/.env.local`. The real `.env` is private to that laptop; never commit or send it. Keep `.env.example` because a fresh setup depends on it.

## How the data moves

| Workflow | Data path |
| --- | --- |
| **EEG → H5** | Browser sends ZIP → FastAPI encrypts it before writing to private storage → worker temporarily decrypts it for validation, de-identification and preprocessing → H5 receives readable numeric EEG → source and review signal are retained encrypted until case deletion; scores go to PostgreSQL. |
| **EEG + video → VEEG review** | Browser sends each clip → FastAPI encrypts it in chunks before private storage → clock/format metadata is checked (no video AI) → after an owner check, playback decrypts requested video chunks. Unsupported formats are prepared only when opened; the encrypted original is retained until case deletion. |
| **Video-only → VSViG** | Browser sends clip → FastAPI encrypts it before private storage → worker temporarily decrypts it for pose extraction and VSViG → result and supported Grad-CAM data are encrypted in PostgreSQL; encrypted video is retained until case deletion. |

**Why decrypt at all?** Encryption protects stored files. H5, OpenPose, and the video player need readable data while they work. The backend decrypts it in a restricted temporary work area, then removes temporary plaintext. The browser only gets protected, owner-authorized responses.

## Security in plain language

- Retained EEG/video files use **AES-256-GCM** and live in private file storage, outside PostgreSQL. Docker keeps encrypted files and database records in separate persistent volumes.
- The backend checks the signed-in account owns the case before returning private EEG, video, or results.
- Selected sensitive database fields and VSViG result payloads are encrypted. EEG scores and routine database metadata are ordinary PostgreSQL values; the application does not encrypt the entire database.
- `MDS01_STORAGE_KEY` is generated in the local `.env`. It is required to read encrypted files. Keep the key private and do not replace it while encrypted recordings still exist; losing it makes those files unreadable.
- Processing uses short-lived plaintext work files. This is temporary disk storage, not memory-only processing.
- The local app uses HTTP on loopback (`127.0.0.1`). File encryption at rest does not provide HTTPS. Do not expose this demo to a network.
- Access is owner-only; this prototype does not provide clinician roles or shared cases.

## Upload limits

These are the default local limits. An individual `.env` can override them.

| Input | Limit |
| --- | --- |
| EEG upload ZIP | Browser accepts just under **2 GiB**; extracted ZIP contents are capped at **2 GiB**. Up to 500 EDF files and 4,096 ZIP entries. |
| Video clip | **512 MiB per clip**, at most **1 hour** and **216,000 frames**. The metadata probe allows up to 1920×1080 and 6–60 FPS. |
| Standalone VSViG clip | Also needs the model’s expected 1920×1080 input by default. Experimental letterbox adaptation is disabled. |

An EEG recording has no single overall duration cap in the upload settings, but file, archive, and signal-size checks still apply. See the [video runbook](docs/video-detection.md) for video-format and pose requirements.

## Stop and restart without losing data

Press **Ctrl-C** to stop the frontend. Then stop the Docker services from the repository root:

```sh
docker compose down
```

This keeps the database and encrypted files. Run `node scripts/demo.mjs` again to restart. **Do not run `docker compose down -v` unless you intend to delete local database records, encrypted recordings, and downloaded model assets.**

## Common setup problems

| Problem | What to do |
| --- | --- |
| Demo says H5 model files are missing | Copy the approved `.h5` and `model-contract.json` into `backend/model/`. |
| Docker is unavailable | Start Docker Desktop, then retry. |
| Video assets fail to initialize | Check internet access, then inspect `docker compose logs vsvig-assets-init`. |
| Backend fails to start | Run `docker compose ps` and `docker compose logs backend`. Do not share logs containing local secrets or patient information. |
| Port 3000, 5432, or 8000 is already in use | Stop the other local service, then retry. |

Use only synthetic or institutionally approved patient data. The app is a local prototype, not an institutional deployment.

## Handover and deeper guides

- [Plain-language backend and encryption walkthrough](docs/backend-handover.md)
- [Setup details, checks, and troubleshooting](docs/setup.md)
- [System architecture and security boundaries](docs/architecture.md)
- [EEG and synchronized VEEG walkthrough](docs/inference-walkthrough.md)
- [VSViG inputs, assets, and known limits](docs/video-detection.md)
- [Documentation index](docs/README.md)

Keep patient data, `.env` files, H5/VSViG assets, and generated reports out of Git.
