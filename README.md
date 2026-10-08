# MDS01

MDS01 is a local research prototype for reviewing EEG and video. EEG inference
and VSViG video inference are separate workflows; their scores are not
automatically combined or synchronized. Outputs are not a diagnosis.

## Run locally

Requirements: Docker Desktop, Node.js 22+, and internet access on first start.

```sh
node scripts/demo.mjs
```

This starts the Docker backend, PostgreSQL, pinned video assets, and browser UI.
Open [MDS01](http://127.0.0.1:3000). The default demo uses the reviewed H5 EEG
model and requires the ignored model artifact and contract listed in
[setup](docs/setup.md). Standalone video analysis uses the pinned VSViG model
assets. Use `node scripts/demo.mjs --development-stub` only for a synthetic
workflow demo; those EEG scores are not model analysis.

Use docker compose down to stop Docker services while keeping local data.
docker compose down -v deletes the database, encrypted files, and video-model
volume. Keep real patient data outside this repository and do not expose the
loopback app to a network.

## Understand the project

- [Plain-language EEG/video inference guide](docs/inference-walkthrough.md)
- [Run and test locally](docs/setup.md)
- [System architecture](docs/architecture.md)
- [Backend guide](docs/backend.md)
- [Video model and failure runbook](docs/video-detection.md)
- [Documentation index](docs/README.md)

Keep model assets, .env files, data, and generated reports local-only.
