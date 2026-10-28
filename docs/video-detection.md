# Video detection runbook

This page covers the separate VSViG video workflow. It is a research prototype,
not a diagnosis, a calibrated probability system, or a guarantee of anonymity.
For the basic explanation, see [inference walkthrough](inference-walkthrough.md).

## How it works

In a combined VEEG case, each uploaded video is encrypted and retained with the
case. Generated local setup sets `MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true`,
so the owner can open unblurred reference playback. A backend with no explicit
value defaults to `false`; that setting controls access only. The upload
request encrypts and saves the original, then returns without decrypting it,
probing metadata, converting it, or invoking OpenPose/VSViG. A restart-safe
background worker later decrypts to a private temporary file to check duration,
frame count/rate, dimensions, container, codec, and audio presence; it deletes
that plaintext and refreshes synchronization matching. `metadata_pending` and
`metadata_checking` describe that separate work. The separate **Video**
workflow submits a clip for VSViG analysis independently of clinical reference
playback.

Browser-compatible H.264/yuv420p MP4 originals with no audio or one AAC track
play from authenticated, owner-checked byte ranges over the encrypted original.
New media is encrypted as independently authenticated AES-256-GCM chunks, so a
range request decrypts only the chunks covering those bytes. Responses are
private/no-store and recheck ownership on every request. After encrypted upload,
the background metadata worker checks clock and browser compatibility. If a
clip is unsupported, it records `conversion_required` but leaves the original
untouched until the owner opens that clip's popup. The protected preparation
request then creates and encrypts an audio-free H.264 review copy while
retaining the original. An H.264/yuv420p source that only needs a container or
audio change is remuxed without re-encoding; other codecs require a full
conversion. This work is format preparation only: it never runs pose readiness
or VSViG. The popup polls status and becomes playable as soon as preparation
completes. Startup recovery resumes a conversion that was already opened and
interrupted; normal metadata and retention sweeps do not start unopened
conversions. The owner-protected preparation endpoint remains available for
retry. The
job exposes `metadata_pending`, `metadata_checking`, `direct`,
`conversion_required`, `processing`, `ready`, `failed`, or `unavailable`
playback state separately from the standalone model job status. A repeated
request reuses the running or completed conversion. Historical monolithic
encrypted videos use a private plaintext cache as a compatibility fallback;
idle cleanup removes it after ten minutes.

```text
combined video → encrypt and retain original → upload acknowledged
    → metadata/sync probe → direct range stream OR background H.264 copy → encrypt
    → owner opens popup → authenticated range stream
standalone analysis → encrypted original → OpenPose readiness → queue → normalization
  → OpenPose keypoints + 15 RGB patches → VSViG window scores
  → unblurred audio-free H.264 review copy
```

For new standalone jobs, the encrypted database result replaces a second
prediction-file artifact. `predictions_path` remains for backward-compatible
reads of older jobs.

Audio is not model input and is not kept in the review video. Encrypted
original and review-video binaries stay in private file storage outside
PostgreSQL and remain until case deletion. New standalone jobs have no expiry.
Migration `035_video_until_deletion` removes deadlines
from existing jobs that have not already expired; it does not restore files
removed by an earlier expiry. In the local demo, original download and
unblurred streaming are enabled for the signed-in owner. A reference-only job
always skips pose and VSViG inference. Standalone video analysis retains its
encrypted original, unblurred review copy, and research results until case
deletion. New VSViG result payloads, including window scores and Grad-CAM
evidence, are compressed and AES-256-GCM encrypted in PostgreSQL. Their nonce
and ciphertext are bound to the owner and job ID. The owner-protected result
route decrypts them for the response; older jobs with an encrypted predictions
file remain readable. Case deletion removes the result fields with the job row
and removes retained files. The ten-minute idle timeout applies only to a
temporary plaintext cache for historical video formats; it does not expire
the retained video or its VSViG result. VSViG receives pose coordinates and
unblurred 32×32 RGB patches; it never receives a full video frame. Keypoints,
extracted patches, and normalized
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

EEG source time is the authoritative playback clock for time, play/pause,
rate, and explicit seek requests. Video follows that clock through validated
clip mappings; routine video `timeupdate` events never reset EEG time. A manual
seek in the video controls maps back to EEG time. The popup is opt-in and
seeking EEG never opens it. When it is open, the shared clock holds while the
mapped video buffers, and the selected clip changes at verified half-open
mapping boundaries. During a genuine video or EEG acquisition gap, video
pauses and the UI reports that no synchronized frame is available; EEG source
time and waveform gaps remain intact. These links align review; they do not
make source markers ground truth or combine EEG and VSViG scores.

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
observations, not results for every HUKM clip.

For playback validation, metadata probing found 27 local AVI clips, all
MPEG-4 at 640×480 and approximately 25 fps; their durations ranged from about
11 seconds to 15 minutes. None qualifies for direct browser playback. In the
current Docker prototype, a 899.9-second MPEG-4 AVI took about 33 seconds from
the first preparation request until status polling ended. Its H.264 copy was
151.9 MB from a 97.4 MB encrypted source. Each full conversion still takes
time. Conversion starts only after the owner opens the clip; opening another
clip can prioritize it over recovery work, but no browser-side request can
cancel an active encode. The frontend avoids queueing clips that are left during
rapid selection. A
13.19-second damaged AVI reproduced the decoder warning `Error at MB: 359` and
produced 329 output frames from 330 indexed source frames. Playback now accepts
at most a one-frame difference when the output duration and other media checks
still pass, and exposes the discrepancy as a review warning. Larger differences
remain unavailable. Timings are local-runtime observations, not performance
guarantees; they exclude browser decode and network transfer.

A separate set of 806 demonstration MP4s had H.264 1920×1080 video streams
with audio. A sample AAC track qualified for direct playback. These demo files
were not used to infer any EEG/video synchronization. An offline diagnostic of
the supplied AVI files and four Nicolet `.e` files found possible unique
metadata candidates for 5 clips, multiple recording candidates for 19, and no
candidate for 3 before upload-group finalization. This is not a completed
owner-case match; no ambiguous clip was forced into sync.

The browser synchronization test remains fixture-backed: it verifies popup
opt-in, status polling and retry/recovery for a conversion-required clip,
EEG-led seek/play/pause, buffering holds, clip mapping boundaries, and the
internal source-clock gap. It does not prove clock accuracy for a completed
real HUKM case. Backend tests verify that metadata probing leaves unsupported
clips unconverted until the owner opens them, direct MP4 range streaming, AVI conversion,
conversion reuse, cross-owner denial, encrypted retention, cache cleanup, and
case deletion. Reference-only jobs do not run VSViG.

This playback change does not optimize EEG waveform page retrieval. The source
signal endpoint still materializes and decrypts the retained source before
reading each requested interval, then removes its plaintext. That can add
latency when navigating long recordings; improving it needs an encrypted
random-access waveform representation or equivalent approach that preserves
the plaintext-cleanup boundary.

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
source-clock alignment when the VEEG metadata has one unique match. Upload
acknowledgement does not wait for background probing; the review page refreshes
pending metadata and sync state. Unmatched clips remain selectable and playable
with their alignment status shown. New chunk-encrypted uploads do not create a
whole-file plaintext cache for streaming; the ten-minute private cache remains
only as a compatibility path for historical monolithic encrypted videos.
Historical face-blurred videos and their labels remain unchanged. The separate
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
