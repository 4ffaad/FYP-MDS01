# System architecture

MDS01 is a local research prototype with a Next.js browser, a FastAPI backend,
relational metadata storage, and private encrypted file storage. The combined
EEG/VEEG review path and standalone VSViG experiment are separate workflows.

The [interactive backend flow map](backend-flow.html) shows request
authorization, the three processing paths, encrypted storage, and temporary
decryption. It links each step to selected source-code excerpts. The
[backend handover](backend-handover.md) explains how to start the app and follow
these paths; the map's editable data is in [backend-flow.json](backend-flow.json).

## VEEG workflow

Combined clinical reference playback is separate from standalone video
analysis. It never requires pose readiness or VSViG inference.
Generated local setup enables MDS01_CLINICAL_VIDEO_REVIEW_ENABLED for owner-only
review; a backend with no explicit value defaults to disabled. The review popup
opens only when the user asks for it. Combined uploads encrypt and retain the
original, then acknowledge without blocking on media probing or video AI. A
restart-recoverable background worker checks the source clock and format and
refreshes matching. Compatible H.264 MP4 streams from authenticated encrypted
byte ranges. An unsupported clip is converted only after the owner opens its
popup; the encrypted original remains retained. This format preparation does
not run OpenPose or VSViG. A verified clip follows the EEG source clock, which
holds during video buffering and never gets reset by routine video time updates.
Genuine acquisition gaps stay visible, and unmatched clips are not presented as
synchronized.

## Boundaries and constraints

- Routes validate requests and return safe responses. Services own workflows;
  repositories own database queries.
- PostgreSQL stores structured state, safe metadata, and results. Recording
  binaries remain in private encrypted file storage.
- Background work runs inside the API process. It is suitable for this local
  prototype, but it is not a durable distributed job queue.
- Access is uploader-only. Local Compose binds to loopback; external hosting,
  HTTPS termination, institution-managed identity, key rotation, and verified
  backup recovery are separate deployment work.

For platforms, model algorithms, the API map, setup requirements, and known
limits, see the [project design](project-design.md). Operational detail remains
in the [setup](setup.md), [backend](backend.md), [frontend](frontend.md), and
[video runbook](video-detection.md).
