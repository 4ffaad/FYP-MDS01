# MDS01

MDS01 is a local research prototype for reviewing EEG and video. A verified
EEG/video metadata match can synchronize owner-only reference playback. The
generated local setup enables it, while an unset backend setting defaults to
off. EEG and VSViG scores remain separate. Human
observations and model flags are review evidence, not a diagnosis or
seizure-onset localization.

The EEG review opens on the fixed 12-second HUKM-style profile (100 µV/cm,
30 mm/s, 0.5–70 Hz plus 50 Hz notch where supported) with the longitudinal
bipolar montage. Combined EEG/video intake creates reference video artifacts
without running VSViG; the separate Video workflow runs VSViG. Standalone video
analysis artifacts are retained encrypted until case deletion. Facial Action
Unit estimates are not produced by the pinned pose/VSViG assets.

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

- [Project design: platforms, algorithms, models, APIs, and runtime](docs/project-design.md)
- [Project goal and success criteria](docs/project-goal.md)
- [Plain-language EEG/video inference guide](docs/inference-walkthrough.md)
- [Run and test locally](docs/setup.md)
- [System architecture](docs/architecture.md)
- [Backend guide](docs/backend.md)
- [Frontend guide](docs/frontend.md)
- [Video model and failure runbook](docs/video-detection.md)
- [Documentation index](docs/README.md)

Keep model assets, .env files, data, and generated reports local-only.
