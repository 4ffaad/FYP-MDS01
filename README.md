# MDS01

MDS01 is a local research prototype for reviewing EEG and video. A verified
EEG/video metadata match can synchronize owner-only reference playback. The
generated local setup enables it, while an unset backend setting defaults to
off. EEG and VSViG scores remain separate. Human
observations and model flags are review evidence, not a diagnosis or
seizure-onset localization.

The standalone VSViG workflow stores its result and Grad-CAM evidence as
AES-GCM-encrypted PostgreSQL data; video files remain encrypted in private file
storage outside the database.

The EEG review opens on the fixed 12-second HUKM-style profile (100 µV/cm,
30 mm/s, 0.5–70 Hz plus 50 Hz notch where supported) with the longitudinal
bipolar montage. Combined EEG/video intake encrypts each original before
background clock and format checks; upload does not wait for those checks and
never runs OpenPose, VSViG, or video conversion. Compatible H.264 MP4 with
optional AAC audio plays directly through authenticated encrypted byte ranges;
unsupported video is converted to an encrypted browser-playable copy only when
opened. The separate Video
workflow runs VSViG. Retained media is encrypted until case deletion. Facial
Action Unit estimates are not produced by the pinned pose/VSViG assets.

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
