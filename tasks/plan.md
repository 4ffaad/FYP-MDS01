# Current engineering work

**Last reviewed: 2026-10-28**

Start with the [backend handover](../docs/backend-handover.md) for setup and
request flows. The [architecture guide](../docs/architecture.md) shows the
security boundaries and model paths.

## Current state

- EEG source review uses 12-second clinical pages and preserves acquisition gaps.
- H5 inference follows the reviewed 18-channel input contract.
- Combined video is encrypted at upload. Background work checks metadata;
  unsupported-format conversion starts only after the owner opens playback.
  Reference review never runs OpenPose or VSViG.
- Standalone VSViG analysis remains a separate experimental workflow.
- Private reads require ownership and use private/no-store responses.
- Backend verification on 2026-10-28: 491 passed, 6 skipped because the local
  OpenCV build lacked codec support. This pass did not run a live
  Docker/PostgreSQL case, real H5 inference, or real-data browser playback.

## Remaining work

1. Repeat a selected-case acceptance run with Docker and approved local data:
   upload, encrypted retention, waveform navigation, popup playback, pause,
   seeking, and source-clock correspondence.
2. Before network deployment, configure HTTPS and institutional access, define
   key rotation, and test recovery of the database and encrypted files together.
3. Validate model outputs with approved assets and datasets. Keep research
   scores and pose failures distinct from clinical findings.

Handover includes the code, startup instructions, model-asset requirements,
test evidence, and these unresolved engineering tasks.
