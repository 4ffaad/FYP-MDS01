# Backend guide

This is the backend's practical map for changing or tracing a request. For a
plain-language model walkthrough, start with
[EEG and video inference](inference-walkthrough.md). API schemas are available
from the running app at http://127.0.0.1:8000/docs.

## How a request is handled

FastAPI routes parse and validate HTTP input. Services own workflows.
Repositories own database queries. Long EEG jobs run through FastAPI
BackgroundTasks after the request returns.

The main EEG path is:

```text
upload → encrypted draft → session → validate → de-identify → preprocess
       → H5 or development stub → save per-window scores → clean temporary files
```

Malformed recordings fail independently. A failed job means no supported score
was produced; it is not a negative seizure result.

## EEG files and model input

Supported inputs are EDF/EDF+, the supported legacy Nicolet .e layout, and
Nicolet .data with its matching .head sidecar.

The legacy .e adapter accepts the reviewed 33-channel, referential, 500 Hz
delivery layout. It maps the reviewed electrode names to the configured
montage, derives the required 18 bipolar channels, and resamples to 256 Hz.
It then writes a separate scrubbed EDF for the common processing path; it
doesn't rewrite the original .e file. Different layouts or ambiguous channels
fail closed. For .e recordings with acquisition gaps, filtering and windows
stay within each observed segment and preserve elapsed offsets.

The model-input contract is:

- 256 samples per second;
- the exact configured 18 bipolar channels, in contract order;
- four-second windows with a two-second stride;
- float32, shape (N, 1024, 18).

Identifying EDF metadata is removed from the derived model input. Relative
event timing may be retained in sanitized form for human review; raw annotation
text is not returned by the public API. Scrubbing metadata does not anonymize
the EEG waveform.

For new `until-deletion` cases, the encrypted original recording is retained
before validation or inference, and the waveform API reads the source directly
even when no model window is flagged. Reads are owner-scoped and bounded by
time range; the browser does not fetch a full multi-hour file at once. For
legacy `.e` files, the viewer can show the reviewed bipolar montage and
available EOG/ECG/chin-difference/photic traces. The uploaded `.e` plaintext
and processing intermediates are removed during cleanup. `ENABLE_FULL_SIGNAL_PREVIEW`
controls the fallback for older retained model-window artifacts that have no
original-source artifact; it does not change new until-deletion source review.
An `.e` range wholly inside a source-clock gap returns an empty preview with no
channels or signal segments; it does not become a server error or synthesize
samples. The shared timestamp vector is sent once, with per-channel timestamps
only for channels whose sampling timeline differs. Signal responses negotiate
gzip and remain `private, no-store`.

For original EDF source review, the backend converts declared V/mV/µV/nV
physical units to volts and fails closed on unknown dimensions. Nicolet `.e`
samples are decoded in volts. Historical scrubbed EDFs with all unit fields
erased are marked `relative-units`; mixed or partially unknown physical units
fail closed. Historical retained NPZ files contain normalized/clipped
model-input values, not physical voltage; their API representation is marked
`normalized-units` or `signal-obfuscated` so the browser presents relative
scales rather than µV. The viewer does not change the model input for display.

## Model runtimes and result meaning

- **Development stub:** deterministic synthetic scores for workflow testing;
  it is not seizure inference.
- **H5:** local Keras artifact and reviewed contract are mounted read-only.
  Startup validates the artifact hash and input/output contract and fails
  closed if either is missing or mismatched.
- **Current output:** research score per EEG window. The supplied local
  contract is uncalibrated; do not describe its score as a probability,
  confidence, accuracy, or recording-level risk. Optional SHAP attribution is
  supplementary and requires an enabled compatible H5 model and reviewed
  background data; a failure leaves valid model scores available. The clinical
  viewer labels it model contribution, not seizure-origin localization.

The H5 model, contract, and SHAP backgrounds are local-only assets. Do not put
them in Git or the Docker image. See [setup](setup.md) for the runtime choice.

## Storage, ownership, and cleanup

PostgreSQL stores accounts, job/session state, safe metadata, EEG score rows,
and the standalone VSViG result payload. New VSViG result payloads, including
Grad-CAM evidence, are AES-GCM encrypted in PostgreSQL and bound to the owner
and job identifier. Legacy file-only results remain readable. Encrypted
EEG/video bytes remain in private filesystem-backed storage. Do not
store patient binaries in PostgreSQL or expose private paths in API responses.
Patient profiles, source reports, EEG archives, original recordings, and video
review copies are encrypted and owner-scoped until case deletion. Combined
video upload encrypts the original and acknowledges it without probing,
conversion, or pose/VSViG work. A restart-recoverable worker checks bounded
metadata after acknowledgement. New VEEG media uses independently authenticated
AES-256-GCM chunks, allowing the owner-authorized range route to decrypt only
requested bytes. Compatible H.264 MP4 with optional AAC audio streams directly;
unsupported formats get an unblurred, audio-free browser
review copy on demand when
`MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true`. The backend fallback is false
when no value is set; generated local setup enables it. When disabled it
blocks reference-only intake, unblurred playback, and original-video download;
the setting controls access and never starts video inference. The patient-folder intake extracts report text locally
for review while retaining the uploaded report inside the encrypted original
archive until case deletion.

Every case, EEG, video, signal, report, media-range, result, observation, and
download route requires an authenticated owner. Responses do not expose
submitted filenames, patient references, filesystem paths, cryptographic
keys, or source bytes outside protected no-store stream/download endpoints.
Original sources and results remain encrypted until case deletion;
response-scoped plaintext and processing intermediates are removed after use.

New EEG and video file envelopes bind AES-GCM authentication to their
storage-relative session, job, and artifact path. Draft promotion re-encrypts
for the final session path. Legacy envelopes remain readable and are atomically
rewrapped after successful materialization when possible. Until every existing
legacy file has been read or explicitly migrated, keep write access to the
private storage volume trusted. Patient profile and source-report encryption
also bind ciphertext to the owner and case.

The storage layer authenticates ciphertext when decrypting it. EEG ingestion
also stores a source SHA-256 value, but the current read path does not compare
every materialized file against that value; this is not an independent
end-to-end integrity monitor. Review access-log configuration before any
shared deployment: default server logs may include client IPs and opaque
resource paths even though application logs avoid patient identifiers.

Signal review uses the protected full-source artifact and requires owner
authentication. New patient analyses do not apply signal obfuscation. Never log
patient-identifying values or raw upload contents.
For metadata-scrubbed legacy `.e` recordings, the encrypted positive-signal
artifact may also include EOG right/left, ECG, chin 1–chin 2, and photic review
traces over the same bounded source-time ranges. These traces are read from the encrypted full-source recording and share the case deletion lifecycle. They are visual review channels and are not model inputs.

Clinical observations are AES-GCM encrypted in PostgreSQL with associated data
bound to the owner, recording, and annotation ID. The observation routes record
the authenticated owner as annotator; only that owner can read the recording's
observations, and deletion is restricted to their own annotation. Current
accounts do not have institution or shared-clinician roles.

The `clinical_access_events` table records an allowlisted action, UTC time,
actor account, and one internal recording/session/video-job row ID. It does not
store patient labels, source names, file paths, request bodies, IP addresses,
or video frames. Case deletion removes linked event rows. These records support
basic access review; they are not a tamper-proof institutional audit service.

## Routes and code locations

Use Swagger for the current complete route schemas. Main route groups:

- /api/auth/ — registration, login, session, logout;
- /api/uploads/ and /api/sessions/ — drafts, EEG sessions, status, deletion;
- /api/recordings/ — predictions, sanitized source annotations, optional
  research attribution, protected signal, encrypted clinical observations;
- /api/cases/ — owner-scoped cases and reviewed profiles;
- /api/video-detection/ — separate VSViG jobs and review playback;
- /api/video-privacy/ — separate protected-video transform.

Combined VEEG upload encrypts the source and returns before metadata probing,
video conversion, or inference. A durable `metadata_pending` row is claimed by
the background worker; startup and retention sweeps re-enqueue pending checks.
The worker removes its private temporary plaintext after probing, refreshes the
encrypted sync mapping, and automatically queues a browser-format copy when
needed. This is format conversion only and never runs OpenPose or VSViG. `POST
/api/video-detection/jobs/{job_id}/playback` is owner-scoped and idempotent; it
promotes the opened clip ahead of queued background conversions and returns
its `processing` state immediately. One background conversion and one
owner-priority conversion may run concurrently. `GET
/api/video-detection/jobs/{job_id}/playback` serves a protected byte-range
stream from either a browser-compatible original or its encrypted review copy.
Each new media chunk is authenticated before it is sent. Old monolithic
encrypted artifacts use a private, idle-cleaned playback cache as a compatibility
fallback. Conversion state is exposed separately from the VSViG job state.

`DELETE /api/cases/{case_id}` removes the owner's linked EEG and video jobs,
encrypted retained media, patient profile, and source report. It returns `409`
while any linked processing job is active.

`GET /api/cases` includes safe workload totals for EEG recordings and video
clips, flagged EEG windows, processing state, and results readiness. Patient
names and short report conclusions appear only from reviewed, owner-scoped
profiles; original filenames and source metadata stay private.

| Start here | Responsibility |
| --- | --- |
| backend/app/main.py | FastAPI setup, routers, startup checks and cleanup |
| backend/app/api/ | HTTP parsing and safe responses |
| backend/app/services/ | Upload, processing, storage, auth and cleanup workflows |
| backend/app/eeg/, backend/app/ml/, backend/app/privacy/ | EEG reading, tensor creation, privacy and inference |
| backend/app/video_detection/ | VSViG/pose runtime and video contract |
| backend/app/database/ | Models, engine, session helper and repositories |
| backend/migrations/versions/ | Alembic schema history |

Use a new Alembic migration for schema changes. Do not rely on create_all()
for runtime schema management.
