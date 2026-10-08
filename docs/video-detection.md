# Video detection runbook

This page covers the separate VSViG video workflow. It is a research prototype,
not a diagnosis, a calibrated probability system, or a guarantee of anonymity.
For the basic explanation, see [inference walkthrough](inference-walkthrough.md).

## How it works

In a combined VEEG case, every uploaded video is retained encrypted with the
source archive. Owner-only reference playback creates an audio-free H.264 copy
without requiring pose readiness, model assets, or VSViG admission. This lets
review continue when analysis is unavailable or a clip cannot be aligned. The
separate **Video** workflow submits a clip for VSViG analysis; it creates the
same reference copy independently of inference success.

```text
combined video → encrypted original → metadata-only preflight → queued reference copy
                                                    └→ unblurred audio-free H.264 → encrypted
standalone analysis → encrypted original → OpenPose readiness → queue → normalization
  → OpenPose keypoints + 15 RGB patches → VSViG window scores
  → unblurred audio-free H.264 review copy
```

Audio is not model input and is not kept in the review video. The encrypted original remains available to its owner until case deletion. The review copy is unblurred; it is available when model admission or inference fails. VSViG receives pose coordinates and unblurred 32×32 RGB patches; it never receives a full video frame. Keypoints, extracted patches, and normalized frames are temporary. Encrypted predictions and review video are retained until case deletion for new jobs. Historical jobs retain their expiry and privacy labels. EEG and video
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
the EEG analysis. If a camera chunk crosses an EEG acquisition gap, the
combined timeline splits that chunk around the gap instead of compressing the
video across it. Footage outside EEG signal segments is labeled as partial
coverage and omitted from the aligned timeline.
Source EEG event times can link directly to a clip timestamp; selecting one
opens the protected video at that time. These links align research review, but
do not make the source markers ground truth or combine EEG and VSViG scores.

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

| Setting                     | Current value                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| Video formats               | AVI, MP4, MOV, WebM                                                                              |
| Native geometry             | 1920×1080                                                                                        |
| Local H5 profile adaptation | Experimental aspect-preserving resize/padding for smaller frames; not equivalent to native video |
| Model-input blur            | New analyses use unblurred RGB patches; historical jobs preserve their recorded setting         |
| Sampling                    | 6 frames/second                                                                                  |
| Model window                | 30 sampled frames (5 seconds)                                                                    |
| Window stride               | 3 sampled frames (0.5 seconds)                                                                   |
| Pose                        | Multiple tracked people; each person is scored as a separate stream using the 15 VSViG joints   |
| Patches                     | 15 RGB patches per sampled frame, each 32×32, extracted from 128×128 keypoint crops              |
| Model output                | One uncalibrated score per window; threshold is 0.5                                              |

The runtime requires timestamps/frames that meet its bounds and all 15
contract-selected pose points for a person in each scored window. It tracks and
scores each person separately, so additional people do not block inference and
their scores are never combined. Track labels follow first detection order;
they do not identify the patient. Three other OpenPose joints are not model
inputs and do not gate inference. `incomplete_pose` and `missing_pose` mark
individual windows without scores; other complete windows and tracks remain
available. A clip with no complete person window produces no score. This is a
model-input quality gate, not a seizure finding.

Native 1920×1080 clips use the same source frames for admission and inference;
they are not re-encoded before pose extraction. Only lower-resolution clips in
the experimental adaptation path are resized and padded.

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
New analyses use unblurred RGB patches by design; the selected condition is
recorded in job provenance. Historical jobs retain their original setting and
privacy label.

## Review output and failures

The prediction API returns window scores, flagged intervals, model provenance,
privacy metadata, and VSViG graph Grad-CAM evidence for the strongest-scoring
window. The CAM is calculated from gradients of the model's time × 15 graph
features, then aligned with the 15 OpenPose patch locations. It shows relative
contribution by sampled time and patch; it is not pixel-level localization or
clinical cause. The API does not return source video. Use /api/video-detection/
in the local [Swagger UI](http://127.0.0.1:8000/docs) for the complete schema.

The unblurred audio-free review video and original source are separate
owner-scoped encrypted artifacts. Reference-copy generation bypasses pose and
VSViG admission, so a model failure does not block playback. The browser offers
slow motion, frame stepping, timestamped bookmarks, and source-clock alignment
when the VEEG metadata has one unique match. Unmatched clips remain selectable
and playable with their alignment status shown. A private range cache expires
after ten idle minutes. Historical face-blurred videos and their labels remain
unchanged. The separate `/api/video-privacy/` utility keeps its own documented
face-local/full-frame fallback policy and does not run VSViG.

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
