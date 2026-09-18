# Video seizure review: VSViG runbook

This is the operator and implementation guide for the visual video-review
workflow. It is a research prototype, not a diagnosis, a calibrated probability
system, or a guarantee of anonymity.

## The boundary

MDS01 has two separate modalities:

- One EEG ZIP archive containing EDF recordings.
- One separate video file.

A paired submission appears in one workspace, but the backend does not put video
inside the EEG archive or run the video model on EEG data.

The video path is:

```text
video upload
  → encrypt source
  → face redaction
  → one shared Lightweight OpenPose keypoint pass
       ├── pose-derived patches → VSViG scores → evidence timeline
       └── full-frame blur + skeleton overlay → privacy-safe video
```

Audio is excluded from every retained visual output and from the visual model
input. The uploaded source can still contain audio while it is encrypted and
waiting for processing; the model and visualization runtime read visual frames
only. The original and temporary full-frame-blurred model-input video files are
deleted after the job. Only an encrypted, owner-scoped privacy-safe
visualization and prediction result are retained until job expiry. The separate
`/video-privacy` utility is audio-free but is not the seizure detector.

## What the GitHub repository provides

The official [VSViG repository](https://github.com/xuyankun/VSViG) is a research
source release, not an end-to-end service. At the pinned revision it provides:

- `VSViG.py`: the STViG/VSViG model implementation.
- `VSViG-base.pth`: the published base checkpoint.
- `extract_patches.py`: Gaussian patch extraction.
- `pose.pth`: a pose-estimation checkpoint.
- `dy_point_order.pt`: dynamic point-partition data used by the model.
- `train.py` and the README, which document training context but are not an
  inference command for arbitrary uploaded videos.

`pose.pth` is interpreted with the [Lightweight Human Pose Estimation
implementation](https://github.com/Daniil-Osokin/lightweight-human-pose-estimation.pytorch).
The VSViG repository does not contain that full import tree, so MDS01 pins and
mounts the required OpenPose source files separately. This is why a VSViG-only
folder produces an asset/runtime error.

The source and weights are research artifacts. A successful checkpoint load
proves technical compatibility; it does not prove accuracy on HUKM footage or
any other new camera/site.

## Model stack

| Stage | MDS01 implementation | Required external asset | Output |
| --- | --- | --- | --- |
| Source protection | AES-GCM upload storage | Installation storage key | Encrypted source bytes |
| Face protection | OpenCV Haar face detector; full-frame Gaussian blur on a miss | OpenCV cascade shipped with the runtime | Protected visual frames plus coverage flags |
| Keypoint extraction | Lightweight OpenPose MobileNet pose network | `pose.pth` plus pinned OpenPose source | One complete 18-joint `(x, y, confidence)` pose |
| Patch construction | Pinned VSViG `extract_patches.py` | `extract_patches.py` | Fifteen `32×32×3` model patches per sampled frame |
| Seizure score | Pinned VSViG STViG/VSViG base model | `VSViG.py`, `VSViG-base.pth`, `dy_point_order.pt` | One uncalibrated score per temporal window |
| Review visualization | Shared pose samples, full-frame blur and OpenCV rendering | No additional model weight | Encrypted audio-free protected video with skeleton overlay |
| Review evidence | Bounded patch occlusion on the strongest flagged window | No additional weight | Input-region sensitivity, not a clinical explanation |

The pose network is the keypoint model. It is not the face-redaction model and it
does not make a seizure decision. The dynamic point-order file is model input
data, not a second classifier.

## Pinned release and provenance

The installer and contract currently pin:

| Dependency | Revision | Role |
| --- | --- | --- |
| [xuyankun/VSViG](https://github.com/xuyankun/VSViG/tree/1026e7e7f2287b96f3cc375830f2836ffdf4588e) | `1026e7e7f2287b96f3cc375830f2836ffdf4588e` | VSViG source, base/pose checkpoints and dynamic partitions |
| [Daniil-Osokin/lightweight-human-pose-estimation.pytorch](https://github.com/Daniil-Osokin/lightweight-human-pose-estimation.pytorch/tree/d23c284b09acf27a163e1febd511e7482cac25ed) | `d23c284b09acf27a163e1febd511e7482cac25ed` | Python implementation for `pose.pth` |
| [VSViG paper](https://arxiv.org/abs/2311.14775) | Published research reference | Clip, patch and temporal-method context |

The installer verifies SHA-256 for every downloaded checkpoint, tensor, Python
source file and retained license. The application verifies the same hashes again
from the mounted `contract.json`; a container cannot approve a changed bundle
with a changed manifest because the manifest hash is supplied separately through
environment configuration.

## One-time Docker setup

Use Docker for the real VSViG path. It is the reproducible project profile and
runs the pinned CPU dependencies in a `linux/amd64` image. Docker Desktop on
Apple Silicon may use emulation and can be slow.

The model executes in the backend container. There are two deployment choices:

| Deployment | Where Docker and the bundle live | Laptop role |
| --- | --- | --- |
| Local development | Docker Desktop and the `mds01-vsvig-assets` named volume | Runs Docker and opens the UI |
| Remote/team deployment | A Linux `amd64` VM, server or managed Docker host with a private image registry and protected model volume | Opens the UI or calls the API; does not run inference |

The default Compose stack uses the same deployment shape locally and remotely:
the `vsvig-assets-init` service downloads and verifies the pinned bundle into the
named Docker volume `mds01-vsvig-assets`, and the backend mounts that volume
read-only at `/opt/vsvig`. The backend checks both the separately configured
`VSVIG_CONTRACT_SHA256` and the code-pinned reviewed contract digest before
startup; a mounted bundle cannot approve its own changed contract. No host
filesystem path is needed for the model.

For a remote deployment, run these commands on the Linux Docker host, not on a
developer laptop. Build and push the application image without model weights,
then run the initializer on the server. If the server pulls from a private
registry, set `VIDEO_DETECTION_IMAGE` in its private `.env` to the immutable
registry tag or digest and run `docker compose ... pull` before `up`; the default
`:local` tag is for an image built on that host. Do not copy a laptop `.env`,
commit checkpoints, or expose the volume to the browser. A private object store
or protected persistent volume can be used to provision the named volume, but
the runtime should still mount the verified bundle read-only.

### 1. Create normal local configuration

From the repository root:

```sh
node scripts/setup.mjs
```

This creates `.env` and `frontend/.env.local` only when they do not exist. It
generates the local database/storage keys and the development demo-admin
password into the ignored `.env`. Read that credential only on the local
machine; it is intentionally absent from this guide, slides and API responses.

### 2. Start the secure one-command stack

The tracked `docker-compose.yml` includes the secure video services. The
initializer uses the Python standard-library installer inside the Docker image.
It downloads only the pinned VSViG files, the
pinned Lightweight OpenPose import tree and the retained licenses. It does not
download patient media or execute downloaded Python. The generated bundle stays
inside the Docker volume and is never copied into the repository. Run one
command from the repository root:

```sh
docker compose up --build
```

Compose builds the video image, runs `vsvig-assets-init` to completion, verifies
the read-only named model volume, applies migrations and starts the backend.
The initializer is idempotent, so normal restarts reuse an already verified
bundle rather than downloading it again.

The upload route performs extension/MIME, model-contract and basic readable
metadata checks before returning `202`. Full video-contract checks (geometry,
constant timing, FPS, readable frame count and pose completeness) run once in the
background path; an invalid clip becomes a terminal failed job rather than
being decoded a second time synchronously. This is intentional for the
asynchronous API and is surfaced through the job error state.

The default bounded transform accepts 6–60 FPS, no more than 1920×1080 pixels,
216,000 decoded frames, 1 GiB of retained preview output and 900 seconds of
privacy-processing wall time. Operators can tune these limits in the private
environment, but increasing them increases CPU, memory, disk and retention risk.

The initializer prints the contract SHA-256 and then performs the tensor-only
runtime verification. A new `.env` created by `node scripts/setup.mjs` already
contains the reviewed hash for the pinned contract. If an older `.env` has no
hash or a different hash, set `VSVIG_CONTRACT_SHA256` in that ignored file to
the value printed by the initializer, then rerun the command. The hash is
public model metadata, not a credential. `VSVIG_ASSET_DIR` is now an internal
container setting (`/opt/vsvig`); do not set a laptop path for it.

For a source/manifest inspection before approval, use the initializer service's
image but omit the approval flag. This intentionally leaves the volume
unreviewed and blocks startup until the normal approved initializer is run
again:

```sh
docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps --entrypoint python vsvig-assets-init \
  backend/scripts/install_vsvig_assets.py --asset-dir /opt/vsvig
```

`--approve-source-contract` means that the pinned source, checkpoint loading,
and MDS01 adapter choices have passed a technical contract review. The upstream
repository does not publish a complete arbitrary-video inference recipe, so this
flag does not prove that every choice matches the authors' hidden training
pipeline. It is not clinical validation, privacy certification or approval to
use the model for patient care. If you want to inspect the generated manifest
first, omit the flag and rerun with the flag after review; an unreviewed manifest
correctly fails closed.

The bundle layout is generated inside the named volume at `/opt/vsvig`:

```text
/opt/vsvig/
├── contract.json
├── VSViG-base.pth
├── pose.pth
├── dy_point_order.pt
├── vsvig/
│   ├── VSViG.py
│   ├── extract_patches.py
│   └── LICENSE
└── openpose/
    ├── demo.py
    ├── val.py
    ├── datasets/
    ├── models/
    ├── modules/
    └── LICENSE
```

Do not move these files into the repository or commit them. Do not replace a
pinned file with a similarly named checkpoint. A replacement requires a new
source revision, hash set, contract review and tests. The volume is initialized
again safely on later starts; already verified files are reused.

### 3. Browser uploads and optional operator diagnostics

The normal browser workflow does not require a host video path. The user selects
a local video in the frontend; the API receives it as multipart form data and
stores it in encrypted backend session storage. The browser never sends an
absolute filesystem path.

`VIDEO_DATA_DIR` is only an optional operator setting for inventory or detector
inspection commands that read an already-approved server-side clip. Do not put
it in the user workflow or ask users to configure it. Mount it explicitly and
read-only for the individual diagnostic command when needed:

```sh
VIDEO_DATA_DIR=/absolute/path/to/approved-video-data
docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps -v "$VIDEO_DATA_DIR:/private-video-data:ro" backend \
  python -m backend.scripts.video_inventory /private-video-data
```

### 4. Explicit verification and recovery commands

The normal command already performs initialization and backend startup
verification. Use these commands only when inspecting a failed or deliberately
removed model volume:

```sh
docker compose run --rm --no-deps vsvig-assets-init
docker compose run --rm --no-deps backend python -m backend.scripts.verify_vsvig_runtime
```

The verification command must print JSON showing `VSViG-base`,
`Lightweight OpenPose`, input shape `[1, 30, 15, 3, 32, 32]`, and output shape
`[1]`. It loads both checkpoints and performs a tensor-only forward pass; it
does not open a video or access patient storage.

The overlay also runs this verification before migrations and Uvicorn startup:

```sh
docker compose up --build
```

If verification fails, the API is intentionally not started. Fix the named
volume, contract hash or dependency rather than enabling a fallback. The
initializer runs as a completed dependency before the backend starts.

Start the frontend in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`, sign in, and choose **New analysis** or **Video
review**. The standalone video route is `/video-detection`.

## Input contract

The current adapter makes its source-informed technical choices explicit in the
generated contract. Values marked as MDS01 choices are not claims that the
upstream release provides a complete inference recipe:

| Field | MDS01 contract value | Reason |
| --- | --- | --- |
| Container | MP4, MOV or WebM readable by OpenCV | Current upload allow-list |
| Geometry | `1920×1080` | Official patch geometry/context; the adapter fails closed instead of silently distorting it |
| Frame timing | Constant frame timing; source FPS at least `6` | The runtime samples the source at 6 FPS |
| Minimum duration | Five seconds of readable visual frames | One complete 30-frame window at 6 FPS |
| Sampled window | `30` frames | 5-second VSViG window |
| Window stride | `3` sampled frames | MDS01 review choice for 0.5-second score spacing; not specified by the upstream reader |
| Pose input | `256` pixel pose height | Lightweight OpenPose demo convention |
| Pose output | 18 joints, each with x, y and confidence | Required complete single-person pose |
| Patch kernel | `128`, Gaussian σ `0.3`, scale `0.25` | Produces `32×32` patches using the pinned extractor |
| Patch tensor | `15×32×32×3`, transposed to `15×3×32×32` | VSViG input per frame |
| Coordinates | x, y, confidence; coordinate scale `1.0` | MDS01 choice because the checkpoint path requires three positional features; upstream comments are inconsistent |
| Pixel values | BGR, pixel scale `1.0` | MDS01 choice preserving OpenCV/source patch values; upstream extractor does not state a color/scale contract |
| Person count | Exactly one usable pose | The v1 adapter never chooses among multiple people |
| Score | Per-window sigmoid output, threshold `0.5` | Research threshold; not calibrated |

The 15 model inputs follow the adapter order reconstructed from the upstream
`train.py` reorder:

```text
nose, left eye, right eye,
right shoulder, right elbow, right wrist,
left shoulder, left elbow, left wrist,
right hip, right knee, right ankle,
left hip, left knee, left ankle
```

These names identify model input regions. They are not causal explanations. The
source release contains preprocessing conventions that are not packaged as a
single official inference command, so the contract records an MDS01 technical
choice and its evidence. Confirm the mapping against the original training
artifacts before making a reproduction claim. Do not claim that a runnable input
contract is the same as validated performance on a new hospital or camera
distribution.

The VSViG paper describes a separate temporal accumulation decision rule. The
current application does not claim to reproduce that final rule; it reports
per-window scores and merges overlapping windows after thresholding. A paper-
faithful accumulation implementation is a remaining research task, not an
implicit feature of this endpoint.

## Privacy and retention

### Detection workflow

1. The multipart upload is written to encrypted application storage before
   background processing. Multipart parsing may use a private short-lived
   framework spool for large parts; that spool is backend-internal and cleaned
   with the job.
2. Processing materializes the source briefly in a job-scoped private work
   directory.
3. OpenCV face detection records coverage and the model-input transform full-frame
   blurs every frame; zero or multiple detections are marked ambiguous.
4. The protected visual file is read for pose/keypoint extraction and VSViG
   scoring. OpenCV writes a video-only model-input file; audio is not decoded
   into model input.
5. The result records face coverage, quality flags and whether human review is
   required. It does not record raw keypoint coordinates.
6. The runtime fans the same in-memory pose samples into two outputs: VSViG
   patches/scores and a visualization that masks the pose region and draws the
   skeleton. It does not run a second pose model. The original and temporary
   model-input files are deleted after success or failure. Only encrypted
   `predictions.json` and `video.visualization.mp4` are retained for the job;
   expiry and startup recovery sweep both artifacts and abandon interrupted
   work.

Face redaction reduces visual exposure but does not guarantee anonymity. Haar
face detection can miss profile, low-light, masked or occluded faces. Coverage
below the job policy fails the detection; intermittent coverage is surfaced as
a review flag. The privacy result is evidence about the transform, not a proof
that no identifying feature remains.

EEG draft uploads are bounded separately from video jobs: the HTTP body is
rejected before multipart parsing when it exceeds the configured upload limit,
each account has a pending-draft count/byte cap, and a background retention
sweep removes expired rows and old orphaned encrypted draft directories. These
limits protect temporary storage but are not a substitute for a host-level
disk quota and encrypted backups policy.

### Separate video-privacy utility

The `/video-privacy` workflow is intentionally different. It can retain an
encrypted audio-free protected output and preview for owner-only review. It is a
privacy transform utility, not the input or evidence artifact for visual
seizure detection.

## API surface

The detection API is intentionally small:

```text
POST /api/video-detection/jobs
GET  /api/video-detection/jobs
GET  /api/video-detection/jobs/{job_id}
GET  /api/video-detection/jobs/{job_id}/predictions
GET  /api/video-detection/jobs/{job_id}/visualization
```

The separate audio-free privacy utility uses:

```text
POST /api/video-privacy/jobs
GET  /api/video-privacy/jobs
GET  /api/video-privacy/jobs/{job_id}
POST /api/video-privacy/jobs/{job_id}/acknowledge
GET  /api/video-privacy/jobs/{job_id}/preview
GET  /api/video-privacy/jobs/{job_id}/download
```

There is no detection source-video endpoint. The `/visualization` endpoint
returns only the encrypted, owner-filtered, audio-free privacy-safe artifact
after authentication; it never returns the original or the internal model-input
video. Result responses contain generated job IDs, status, privacy provenance,
model provenance, window scores, a time-indexed timeline, merged events,
summary metadata and optional patch-sensitivity evidence. They do not contain
patient references, original filenames, storage paths, raw video, audio or pose
coordinates. Normal users are owner-filtered; the development demo
administrator can review local users’ records.

The prediction response adds review-oriented projections without exposing raw
keypoints:

```json
{
  "timeline": [{"timestamp": 2.0, "start_time": 1.0, "end_time": 3.0, "score": 0.8, "seizure_detected": true}],
  "events": [{"start_time": 1.0, "end_time": 3.0, "peak_score": 0.8, "peak_timestamp": 2.0}],
  "summary": {"peak_score": 0.8, "potential_event_detected": true, "event_count": 1, "threshold": 0.5},
  "visualization": {
    "available": true,
    "media_type": "video/mp4",
    "audio_included": false,
    "privacy_method": "full-frame-blur-and-skeleton-overlay",
    "overlay": {"skeleton": true, "model_score": false, "event_markers": false},
    "frontend_overlay": {"model_score": true, "event_markers": true}
  }
}
```

The timeline timestamp is the midpoint of each VSViG window. Event boundaries
are produced by the existing configured per-window threshold and overlap merge;
no new clinical threshold is introduced. The frontend score and event overlays
are synchronized views of these stored values, not a second inference pass.


```text
queued → preflight → privacy-transform → pose-and-inference (model + protected visualization) → complete
```

Failure and expiry are terminal states. A separate background task processes one
job at a time in the current prototype.

## Why the error appears

The old message, “Mount the official model assets before starting detection,” is
the safe response when the service cannot see a valid named-volume bundle. The
current messages map to these causes:

| Error code/message family | Meaning | Fix |
| --- | --- | --- |
| `assets_missing` | The named volume is empty or `/opt/vsvig`/`contract.json` is absent | Run `vsvig-assets-init` with the two-file Compose command |
| `contract_unreviewed` | The manifest hash is absent/wrong or the contract was generated without review approval | Set the ignored `.env` hash to the initializer output and rerun the initializer |
| `asset_mismatch` | A pinned checkpoint/source/license/partition hash, repository or revision differs | Reinstall the pinned bundle; do not substitute a checkpoint |
| `contract_invalid` | A required preprocessing field or shape is malformed | Regenerate the contract; do not hand-edit values to bypass validation |
| `runtime_incompatible` | PyTorch, timm, OpenCV, the OpenPose import tree or either checkpoint failed to load | Run `verify_vsvig_runtime`; rebuild the overlay image |
| `video_incompatible` | The clip is not readable, constant-timed, `1920×1080`, at least 6 FPS, or long enough | Convert a consented demo clip to the input contract |
| `privacy_transform_failed` | Face-redaction output could not be validated or coverage was too low | Inspect detector coverage; use a clearer one-person clip |
| `visualization_failed` | The protected audio-free review artifact could not be encoded or validated | Check the video runtime/codec and retry the consented clip |
| `ambiguous_or_missing_pose` / `incomplete_pose` | No single complete pose was available | Use one visible person with adequate framing and lighting |
| `no_usable_windows` | No complete 30-sampled-frame window was produced | Use at least five seconds of readable video |

Do not put exception traces, local paths, filenames or patient media into a bug
report. The worker deliberately converts upstream exceptions into fixed public
error codes.

## Inspection and evaluation

The inventory helper reports aggregate media counts, durations, frame rates and
resolutions without printing filenames or file contents:

```sh
docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps -v "$VIDEO_DATA_DIR:/private-video-data:ro" backend \
  python -m backend.scripts.video_inventory /private-video-data
```

For approved local detector inspection, write any annotated output outside the
repository and delete it afterward. An annotated video contains source
appearance and is not an evidence artifact:

```sh
mkdir -p /tmp/mds01-vision-check
docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps -v "$VIDEO_DATA_DIR:/private-video-data:ro" \
  -v /tmp/mds01-vision-check:/out backend \
  python -m backend.scripts.inspect_video_vision \
  /private-video-data/approved-clip.mp4 \
  --mode haar --output /out/face-detector-check.mp4
```

Detector coverage is not seizure-detection accuracy. Accuracy requires
clinician-reviewed onset/offset labels, patient-disjoint splits and a declared
evaluation unit. Use [presentation-readiness.md](presentation-readiness.md) for
the complete scientific, privacy and deployment checklist.

## Verification checklist

Run the checks that apply to the change. The practical commands are:

```sh
docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps vsvig-assets-init

docker compose -f docker-compose.yml -f docker-compose.video-detection.yml \
  run --rm --no-deps backend python -m backend.scripts.verify_vsvig_runtime

.venv/bin/python -m unittest discover -s backend/tests
cd frontend
npm run format:check
npm run lint
npx tsc --noEmit
npm run build
```

The full backend suite and frontend checks verify application contracts; they do
not measure VSViG accuracy. A real model demo additionally needs an approved,
non-patient or consented clip satisfying the input contract.

## HUKM and presentation gate

Before using a HUKM clip or claiming a result, obtain the approved retrospective
use/consent decision, retention policy, access list and model-license review.
Keep the identity key at HUKM. Prepare patient-disjoint evaluation splits with
reviewed visible-event onset/offset labels and document the relationship between
EEG onset, visible onset, clock offsets and drift.

Measure at minimum:

- event sensitivity/recall and false alarms per hour;
- precision, specificity, F1 and precision-recall performance where justified;
- onset latency and confidence intervals;
- face-redaction coverage and false-negative face cases;
- raw-versus-redacted score drift;
- CPU latency, memory and safe concurrency;
- behavior for multiple people, staff entry, occlusion, poor lighting and no
  pose.

Keep the presentation wording at “research prototype”, “uncalibrated model
score”, “flagged interval for human review” and “face-redacted model input” until
those gates are complete. Do not use “anonymous”, “confidence”, “validated
seizure detector”, “real-time” or “safe for clinical use” without separate
reviewed evidence.
