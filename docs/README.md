# Documentation map

Start with the document that matches the task. The README is the short project
overview; this page is the maintained map for teammates.

| If you need to… | Read | Skip unless needed |
| --- | --- | --- |
| Run the application or tests | [Setup](setup.md) | Research/runtime options |
| Understand system boundaries and find code | [Architecture](architecture.md) | Implementation details |
| Change browser screens or API calls | [Frontend guide](frontend.md) | Backend internals |
| Change API, processing or persistence | [Backend guide](backend.md) | Browser implementation |
| Set up or review VSViG detection | [Video detection](video-detection.md) | EEG calibration material |
| Prepare the demo/presentation | [Presentation readiness](presentation-readiness.md) | Deployment runbooks |
| Understand visual rules | [Design rules](../DESIGN.md) | Component implementation |

For the shortest handoff, read [Setup](setup.md) first, then use the
architecture guide only when you need to change code. `npm run format` keeps
frontend formatting consistent; `npm run lint` and the test commands are the
checks used before handoff.

## Evidence and limitations

These are supporting records, not setup instructions or proof of clinical
performance:

- [EEG confidence research](eeg-viewing-and-confidence-research.md) explains
  the per-window calibration design.
- [Privacy research](privacy-research.md) records de-identification limits and
  evaluation questions.
- [Security audit](security-audit.md) is a deployment-risk checklist.
- [VSViG research](vsvig-research.md) records the upstream source facts used by
  the pinned runtime contract.

## Source of truth

- Runtime behavior: code and tests.
- API and EEG model contracts: the mounted H5 contract at `/opt/eeg-model/model-contract.json`
  and the route schemas. Video model provenance and preprocessing: [video detection](video-detection.md)
  plus the generated external `contract.json`.
- Database schema: current Alembic migrations.
- Patient data, model weights, calibration backgrounds, `.env`, and reports:
  local only, never Git.
