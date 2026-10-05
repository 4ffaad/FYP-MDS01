# Video detection runbook

This page covers the separate VSViG video workflow. It is a research prototype,
not a diagnosis, a calibrated probability system, or a guarantee of anonymity.
For the basic explanation, see [inference walkthrough](inference-walkthrough.md).

## How it works

In the app, upload from **Video** and open jobs from **Video reviews**. A job
that passes readiness runs VSViG and creates its protected review video. A
readable clip rejected by the model gates can still get a privacy-only review
copy; its job remains failed and has no VSViG score. The old `/video-privacy`
page redirects to this workflow.

```text
encrypted upload
  → OpenPose readiness check on the opening five-second window
  ├→ gate rejected → face blur (full-frame fallback) → encrypted review copy; no score
  └→ gate passed → queue → temporary timestamp/geometry normalization
       → OpenPose keypoints and 15 RGB patches from temporary source frames
       → blur each patch ─────────────────────────────────────────→ VSViG window scores
       → face-blurred review video, with full-frame fallback and skeleton
```

Audio is not model input and is not kept in the review video. The encrypted
source may contain audio while queued, then is deleted after processing. A
rejected but readable clip is retained only until its privacy-only copy is
validated; if that transform fails, its source is deleted and no player appears.
VSViG receives pose coordinates and individually blurred 32×32 RGB patches; it
never receives a full video frame. Keypoints, extracted patches, and
source/intermediate frames are temporary. Encrypted predictions and the
redacted review video are retained until job expiry when generated. Rejected
clips retain only the review video, with no prediction artifact. EEG and video
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
| Model-input blur            | Each of the 15 extracted patches is blurred independently; UI accepts 50–100%                    |
| Sampling                    | 6 frames/second                                                                                  |
| Model window                | 30 sampled frames (5 seconds)                                                                    |
| Window stride               | 3 sampled frames (0.5 seconds)                                                                   |
| Pose                        | One tracked person; confidence and bounds are checked on the 15 joints used by VSViG             |
| Patches                     | 15 RGB patches per sampled frame, each 32×32, extracted from 128×128 keypoint crops              |
| Model output                | One uncalibrated score per window; threshold is 0.5                                              |

The runtime requires timestamps/frames that meet its bounds and all 15
contract-selected pose points on every sampled frame. The pinned patch extractor
drops three of OpenPose's 18 joints, so those unused joints do not gate VSViG;
they are omitted from tracking when confidence is too low. `incomplete_pose`
means at least one required point was missing, too uncertain, or out of frame.
Inference stops before VSViG and no score is produced. It does not mean no
seizure. Use one visible person with clear framing and lighting; do not weaken
the pose gate for the 15 points that the model actually uses.

Native 1920×1080 clips use the same source frames for admission and inference;
they are not re-encoded before pose extraction. Only lower-resolution clips in
the experimental adaptation path are resized and padded.

Before queueing, upload admission runs the pinned pose model on the first
30 samples (five seconds at 6 fps), without loading or calling VSViG. It checks
for exactly one trackable person and all 15 landmarks at every sample. The
preflight response reports counts and missing landmark names, never frames or
coordinates. This is an early readiness check only: inference checks every
sample in the full clip, so a later pose failure can still stop processing. The
gate counts detected people; it cannot establish that the person is the patient.

The processing status shows the active backend stage (**Preparing video** or
**OpenPose and VSViG**). Clips from a folder intake are uploaded as queue
capacity allows. A 429 response means the current clip was not accepted; when
this intake already has accepted work, the browser waits for one of those jobs
to finish and retries that clip. It never retries an upload whose acceptance
is uncertain.

The resize/padding option cannot recover missing detail. Keep adapted inputs
labelled experimental and evaluate them separately from native 1920×1080 clips.
The selected blur strength is recorded with the job. Values below 50% are
rejected; reducing blur can expose more visual detail, so keep it at the
reviewed default unless the research protocol explicitly requires a comparison.

## Review output and failures

The prediction API returns window scores, flagged intervals, model provenance,
privacy metadata, and VSViG graph Grad-CAM evidence for the strongest-scoring
window. The CAM is calculated from gradients of the model's time × 15 graph
features, then aligned with the 15 OpenPose patch locations. It shows relative
contribution by sampled time and patch; it is not pixel-level localization or
clinical cause. The API does not return source video. Use /api/video-detection/
in the local [Swagger UI](http://127.0.0.1:8000/docs) for the complete schema.

The review video is a separate owner-scoped encrypted artifact. Each output
frame uses tracked OpenPose head landmarks to blur the face; missing, stale,
incomplete, or ambiguous face landmarks trigger full-frame blur. The skeleton
overlay is drawn after the privacy transform. In the browser, reviewers can
add blur over the same 15 128×128 keypoint regions used to form VSViG's 32×32
input patches, and can apply a full-frame display blur. These viewer overlays
do not change the stored video or model result. The public example frame under
`frontend/public/examples/` demonstrates upstream face blur and is labeled as
a reference, not an MDS01 output. Playback uses a private cache that expires
after ten idle minutes. The separate `/api/video-privacy/` utility retains its
own face-local/full-frame fallback policy and does not run VSViG.

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
| ambiguous_or_missing_pose, incomplete_pose          | The clip did not provide one acceptable full pose. No VSViG score was produced.                                   |
| visualization_failed                                | The protected review video could not be safely produced. No completed result is published.                        |

Treat video output as an uncalibrated research score for human review. A
successful startup or synthetic tensor check does not establish model accuracy,
privacy effectiveness, or equivalence to the published method.
