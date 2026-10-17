# Video detection runbook

This page covers the separate VSViG video workflow. It is a research prototype,
not a diagnosis, a calibrated probability system, or a guarantee of anonymity.
For the basic explanation, see [inference walkthrough](inference-walkthrough.md).

## How it works

In a combined VEEG case, every uploaded video is retained encrypted with the
source archive. Generated local setup sets
`MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true`, so the owner can open unblurred,
audio-free reference playback. A backend with no explicit value defaults to
`false`; that setting controls access only and does not invoke OpenPose or
VSViG. The reference copy is created independently of pose readiness, model
assets, and VSViG admission. The separate **Video** workflow submits a clip
for VSViG analysis independently of clinical reference playback.

Reference preparation is a separate serialized media task: it removes audio,
converts sources that need it to browser-playable H.264, validates the
encrypted review copy, and retains the encrypted original. It never runs pose
readiness or VSViG. The worker validates the review copy's indexed frame count
and stream metadata against the source container estimate, avoiding a second
full decode solely to count frames after FFmpeg has completed the conversion.
Non-browser-playable formats such as AVI still require a full conversion
before they can play in the browser.

```text
combined video → encrypted original → metadata-only sync metadata
    → owner review access → unblurred audio-free H.264 → encrypted
standalone analysis → encrypted original → OpenPose readiness → queue → normalization
  → OpenPose keypoints + 15 RGB patches → VSViG window scores
  → unblurred audio-free H.264 review copy
```

Audio is not model input and is not kept in the review video. The encrypted
original, review copy, and predictions are encrypted in private file storage
outside PostgreSQL and retained until explicit case deletion. New standalone
jobs have no expiry. Migration `035_video_until_deletion` removes deadlines
from existing jobs that have not already expired; it does not restore files
removed by an earlier expiry. In the local demo, original download and
unblurred streaming are enabled for the signed-in owner. A reference-only job
always skips pose and VSViG inference. Standalone video analysis retains its
encrypted original, unblurred review copy, and research results until case
deletion. VSViG receives pose coordinates and unblurred 32×32 RGB patches; it never
receives a full video frame. Keypoints, extracted patches, and normalized
frames are temporary. EEG and video
jobs run independently. The combined view links them only when the uploaded
clip group, VEEG clock anchors, frame counts, and frame rate produce a unique
metadata match. Unmatched and ambiguous clips stay separate; a metadata match
does not prove that the uploaded bytes are the original acquisition.

## Nicolet EEG and video synchronization

When a patient-folder upload contains a legacy Nicolet `.e` recording and its
video clips, the browser keeps each selected camera directory as an opaque group.
The backend reads the `.e` `VIDEOSYNCGUID` section, HMACs each referenced video
basename with a case-scoped key context, and encrypts the clock/frame anchors
at rest. Raw video names are used transiently for matching; they are not
persisted or returned. Folder finalization compares the selected basename
manifest with the accepted uploads before resolving timestamps.

The parser uses the observed 752-byte section prefix and 600-byte rows: frame
number, source clock timestamp, and a UTF-16 video reference. This layout has
been checked against the supplied local recordings, but is not an official
Nicolet file-format specification. Each clip is linked only when its filename
token, frame count, frame rate, and clock anchors identify one recording among
the complete uploaded groups. Repeated names, missing chunks, inconsistent
timing, or multiple matches leave the clips unpaired. This establishes a
unique metadata match among submitted clips, not the identity of the original
video bytes.

The stored mapping uses the EEG source clock, matching the timestamps shown by
the EEG analysis. A uniquely matched clip remains continuous across internal
EEG acquisition gaps; the video frame clock is not compressed or shifted to
hide missing EEG samples. The waveform shows an explicit no-samples interval,
and `eeg_coverage_seconds` reports only the part of video time that overlaps
recorded EEG. Video before the first or after the last EEG source segment is
omitted from the aligned timeline.

EEG navigation and the video element use one owner-controlled playback state
for source time, play/pause, rate, and explicit seek requests. Video position
updates the shared EEG time; the current clip auto-switches at verified
half-open mapping boundaries. During a video gap, video pauses and shows an
unavailable state while the EEG timeline may continue. Starting, seeking, and
crossing EEG pages do not create a second independent playback clock. Selecting
a model flag or source annotation seeks the same shared time when video
coverage is available. These links align review; they do not make source
markers ground truth or combine EEG and VSViG scores.

Safe sync diagnostics include `incomplete_folder`, `missing_reference`,
`clock_mismatch`, `frame_mismatch`, `ambiguous`, and `unmatched`. They identify
why a clip has no verified EEG mapping. They do not prevent independent
owner-authorized playback of an available reference copy.

## Run it locally

Use the Docker app from [setup](setup.md). The video model runs inside the
backend container. The one-shot vsvig-assets-init Compose service downloads
and verifies pinned assets into a named volume mounted read-only at /opt/vsvig.
The model weights and source files are not in Git or in the application image.

Check runtime assets when troubleshooting:

```sh
docker compose exec -T backend python -m backend.scripts.verify_vsvig_runtime
```

A successful check confirms that pinned assets load and the model accepts the
expected tensors. It does not run a video or prove the pose gate will pass.
Do not change hashes or the reviewed contract to silence a verification error.

## Pinned sources

| Asset                                                                                                                                            | Pinned revision                          | Use                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- | -------------------------------------------------------- |
| [VSViG](https://github.com/xuyankun/VSViG/tree/1026e7e7f2287b96f3cc375830f2836ffdf4588e)                                                         | 1026e7e7f2287b96f3cc375830f2836ffdf4588e | VSViG model, checkpoint and patch extractor              |
| [Lightweight OpenPose](https://github.com/Daniil-Osokin/lightweight-human-pose-estimation.pytorch/tree/d23c284b09acf27a163e1febd511e7482cac25ed) | d23c284b09acf27a163e1febd511e7482cac25ed | Pose implementation used with the published pose.pth     |
| [VSViG paper](https://arxiv.org/abs/2311.14775)                                                                                                  | Published paper                          | Research context; not a complete upload-inference recipe |

The named volume contains VSViG-base.pth, pose.pth, dy_point_order.pt, the
pinned Python sources, licenses, and a generated contract.json. The initializer
and backend check the asset hashes and reviewed contract. Never replace a file
with a similarly named checkpoint or commit model assets. The upstream release
does not provide a complete inference recipe for arbitrary videos; some adapter
details are MDS01 research choices.

## Input and score contract

| Setting                        | Current value                                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Video formats                  | AVI, MP4, MOV, WebM                                                                                        |
| Native geometry                | 1920×1080                                                                                                  |
| Letterbox adaptation           | Experimental; disabled by default; requires explicit `VSVIG_ALLOW_LETTERBOX_ADAPTATION=true`; not equivalent to native video |
| Model-input blur               | New analyses use unblurred RGB patches; historical jobs preserve their recorded setting                   |
| Clinical review-video gate     | `MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true` in generated local setup; backend fallback is `false`           |
| Sampling                       | 6 frames/second                                                                                            |
| Model window                   | 30 sampled frames (5 seconds)                                                                              |
| Window stride                  | 3 sampled frames (0.5 seconds)                                                                             |
| Pose                           | Multiple tracked people; each person is scored as a separate stream using the 15 VSViG joints             |
| Patches                        | 15 RGB patches per sampled frame, each 32×32, extracted from 128×128 keypoint crops                       |
| Model output                   | One uncalibrated score per window; threshold is 0.5                                                        |

The runtime's model tensor contract is patches with shape
`[B, 30, 15, 3, 32, 32]` and pose coordinates/confidence with shape
`[B, 30, 15, 3]`. The selected patch order is nose, left eye, right eye,
right shoulder/elbow/wrist, left shoulder/elbow/wrist, right hip/knee/ankle,
then left hip/knee/ankle. Neck and ears are not model inputs. This is not a
requirement for a complete 18-joint
skeleton, but it does require every selected landmark for one person at every
sample in a scored 30-frame window. The adapter has no reviewed missing-joint
mask, so it fails closed for an incomplete window; missing points are not
fabricated or interpolated.

It tracks and scores each detected person separately, so additional people do
not block inference and their scores are never combined. Track labels follow
first detection order; they do not identify the patient and may not remain a
reliable identity across occlusion. Three other OpenPose joints are not model
inputs and do not gate inference. `incomplete_pose` and `missing_pose` mark
individual windows without scores; other complete windows and tracks remain
available. A clip with no complete person window produces no score. This is a
model-input quality gate, not a seizure finding.

Native 1920×1080 clips use the same source frames for admission and inference;
they are not re-encoded before pose extraction. Lower-resolution clips are
resized and padded only when the experimental `VSVIG_ALLOW_LETTERBOX_ADAPTATION`
setting is explicitly enabled; it is off by default.

Before queueing, upload admission runs the pinned pose model on the first
30 samples (five seconds at 6 fps), without loading or calling VSViG. It accepts
the clip when at least one person has all 15 selected landmarks throughout a
complete opening window. Multiple people are allowed. The preflight response
reports counts and missing landmark names, never frames or coordinates. This is
an early readiness check only: later windows can remain unscored when a track
disappears or selected landmarks are incomplete. The gate cannot establish
which track is the patient.

The processing status shows the active backend stage (**Preparing video** or
**OpenPose and VSViG**). Clips from a folder intake are uploaded as queue
capacity allows. A 429 response means the current clip was not accepted; when
this intake already has accepted work, the browser waits for one of those jobs
to finish and retries that clip. It never retries an upload whose acceptance
is uncertain.

The resize/padding option cannot recover missing detail. Keep adapted inputs
labelled experimental and evaluate them separately from native 1920×1080 clips.
It is disabled by default and requires explicit operator opt-in.
New analyses use unblurred RGB patches by design; the selected condition is
recorded in job provenance. Historical jobs retain their original setting and
privacy label.

## Bounded demonstration evidence

The pinned runtime and asset verification passed, and the standalone validated
demo clip completed pose extraction, patch generation, and VSViG inference in
the local research runtime. Its observed score was `0.782`; this is an
uncalibrated research score, not a probability, accuracy claim, or clinical
finding. The demo clip is separate from HUKM patient recordings.

A low-resolution supplied HUKM AVI sample was 640×480. The native path rejects
that geometry; in a bounded diagnostic run with experimental adaptation
explicitly enabled, one person track was found but selected landmarks were
absent in 22 of 30 sampled frames, chiefly knees and ankles, so no VSViG score
was produced. Adaptation is now disabled by default. A separate two-person test
detected two tracks, but neither had a complete supported window. The tracker
keeps tracks separate and does not choose the patient. These are bounded
observations, not results for every HUKM clip. The earlier reported 26-video
set and its 17/9 match count were not reproduced in this verification; the
exact supplied selection remains unverified.

The local HUKM VEEG case was then verified separately for clinical playback:
all 10 uploaded clips reached `ready`, had a unique EEG mapping, and returned
owner-protected encrypted original and review artifacts with no expiry. A real
browser opened a mapped clip; its protected media request returned HTTP 206 for
a byte range, and EEG play/pause advanced the shared source clock with the
video. None of these reference-only jobs had VSViG predictions. One source
advertised 330 frames but yielded 329 decodable frames. Review-copy validation
now uses the decodable count, preserves those frames, and exposes a warning;
the EEG mapping continues to use the original clock anchors. The exact 26-clip
selection remains unverified.

## Review output and failures

The prediction API returns window scores, flagged intervals, model provenance,
privacy metadata, and VSViG graph Grad-CAM evidence for the strongest-scoring
window. The CAM is calculated from gradients of the model's time × 15 graph
features, then aligned with the 15 OpenPose patch locations. It shows relative
contribution by sampled time and patch; it is not pixel-level localization or
clinical cause. The API does not return source video. Use /api/video-detection/
in the local [Swagger UI](http://127.0.0.1:8000/docs) for the complete schema.

The review video can include an OpenPose body-skeleton overlay when pose samples
are available, plus the score and Grad-CAM overlays in the browser. Facial
action-unit estimates are not part of the pinned pose/VSViG pipeline and are
not produced or displayed. A missing pose overlay does not invalidate the
underlying source video in the local owner-review workflow.

The unblurred audio-free review video and original source are separate
owner-scoped encrypted artifacts. Reference-copy generation bypasses pose and
VSViG admission, so a model failure does not block playback. Generated local
setup enables original download, unblurred range streaming, and reference-only
intake for the signed-in owner; a backend with no explicit value keeps the
access switch off. New jobs retain encrypted media and results until case deletion. The
browser offers slow motion, frame stepping, timestamped bookmarks, and
source-clock alignment when the VEEG metadata has one unique match. Unmatched
clips remain selectable and playable with their alignment status shown. The
short-lived private range cache expires after ten idle minutes. Historical
face-blurred videos and their labels remain unchanged. The separate
`/api/video-privacy/` utility keeps its own documented face-local/full-frame
fallback policy and does not run VSViG.

Video decoding and model inference currently run in the backend container under
the backend service account. Compose limits the service, but it does not isolate
native media decoders from the API process's private-storage mount or network.
Use a separate, restricted worker before exposing video processing to untrusted
uploads or a shared network deployment.

| Error                                               | What it means                                                                                                     |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| assets_missing, asset_mismatch, contract_unreviewed | The external bundle is absent, changed, or not approved; fix the pinned setup rather than bypassing verification. |
| runtime_incompatible                                | A required dependency, source file, or checkpoint failed to load.                                                 |
| video_incompatible                                  | The clip is unreadable or violates timing, frame-rate, duration, or size limits.                                  |
| video_resolution_mismatch                           | The clip is not native 1920×1080 and experimental adaptation is disabled.                                         |
| ambiguous_or_missing_pose, incomplete_pose          | No complete 15-point person window was available; incomplete windows remain unscored.                               |
| visualization_failed                                | The protected review video could not be safely produced. No completed result is published.                        |

Treat video output as an uncalibrated research score for human review. A
successful startup or synthetic tensor check does not establish model accuracy,
privacy effectiveness, or equivalence to the published method.
